# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The host's HTTP/1.1 server, on asyncio streams and nothing else.

Written for this host only: it reads a request, routes it to a controller by method and path,
binds the JSON body into the controller's model, and writes back what the controller answered,
as ASP.NET writes it. Connections stay open between requests unless the caller asks to close
(HTTP/1.1 keep-alive).
"""

from __future__ import annotations

import asyncio
import re
import secrets
import urllib.parse
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from email.utils import formatdate
from http import HTTPStatus
from typing import Any

from standard_agents.agent import Agent
from standard_agents.host import wire
from standard_agents.host.controllers.action_results import ObjectResult, StreamResult
from standard_agents.host.controllers.agents_controller import AgentsController
from standard_agents.host.controllers.home_controller import HomeController
from standard_agents.host.controllers.v1.agents_v1_controller import AgentsV1Controller
from standard_agents.host.http_context import HttpContext, HttpContextAccessor
from standard_agents.host.models.agent_run_request import AgentRunRequest
from standard_agents.host.models.v1.agent_run_request_v1 import AgentRunRequestV1
from standard_agents.host.security import api_key_gate, identity_gate
from standard_agents.host.security.claims import ClaimsPrincipal

_PERCENT_ENCODED_SLASH = re.compile(r"(%2[Ff])")


@dataclass(frozen=True)
class HttpRequest:
    """One request as the server read it: what an authentication scheme and a route look at.

    Header names are lower case; a header sent more than once reads as its values joined with
    a comma, as ASP.NET's StringValues reads.
    """

    method: str
    path: str
    version: str
    headers: Mapping[str, str]
    body: bytes = b""

    @property
    def keep_alive(self) -> bool:
        connection_options = {
            option.strip().lower()
            for option in self.headers.get("connection", "").split(",")}

        if self.version == "HTTP/1.0":
            return "keep-alive" in connection_options

        return "close" not in connection_options


@dataclass(frozen=True)
class _Route:
    method: str
    template: str
    request_type: type | None
    # The controller action, handed the agent as a callable so a route that needs no agent
    # (the heartbeat) never composes one, the route's bound model, and the request's
    # cancellation.
    action: Callable[
        [Callable[[], Agent], Any, asyncio.Event],
        Awaitable[ObjectResult | StreamResult]]

    def matches(self, path: str) -> bool:
        # Routes match ignoring case, and a trailing slash, as ASP.NET's routing matches them.
        segments = path.removeprefix("/")

        if segments.endswith("/"):
            segments = segments[:-1]

        return segments.upper() == self.template.upper()


async def _get_home(agent, request, cancellation):
    return HomeController().get()


async def _post_run(agent, request, cancellation):
    return await AgentsController(agent()).post_run(request, cancellation=cancellation)


async def _post_stream(agent, request, cancellation):
    return await AgentsController(agent()).post_stream(request, cancellation=cancellation)


async def _post_v1_run(agent, request, cancellation):
    return await AgentsV1Controller(agent()).post_run(request, cancellation=cancellation)


async def _post_v1_stream(agent, request, cancellation):
    return await AgentsV1Controller(agent()).post_stream(request, cancellation=cancellation)


_ROUTES = (
    _Route("GET", "api/Home", None, _get_home),
    _Route("POST", "api/Agents/runs", AgentRunRequest, _post_run),
    _Route("POST", "api/Agents/streams", AgentRunRequest, _post_stream),
    _Route("POST", "api/V1/agents/runs", AgentRunRequestV1, _post_v1_run),
    _Route("POST", "api/V1/agents/streams", AgentRunRequestV1, _post_v1_stream),
)


class AgentHost:
    """The host: the routes, the gates in front of them, and the agent behind them.

    The agent is resolved at the first request that needs it and reused for every request
    after, as the C# host resolves its singleton IAgent: one instance serves prompts
    concurrently, and run state is per invocation (SPEC.md 4.4).
    """

    def __init__(
            self,
            resolve_agent: Callable[[], Agent],
            *,
            urls: Sequence[str] = ("http://localhost:5000",),
            api_key: str | None = None,
            authentication_configured: bool = False,
            authenticate: Callable[[HttpRequest], Awaitable[ClaimsPrincipal | None]] | None = None,
            http_context_accessor: HttpContextAccessor | None = None) -> None:

        self._api_key = api_key
        self._authentication_configured = authentication_configured
        self._authenticate = authenticate
        self._http_context_accessor = http_context_accessor or HttpContextAccessor()
        self._resolve_agent = resolve_agent
        self._agent: Agent | None = None
        self._configured_urls = tuple(urls)
        self._servers: list[asyncio.AbstractServer] = []
        self._connections: set[asyncio.Task] = set()

    @property
    def urls(self) -> tuple[str, ...]:
        """The addresses the host listens on, with the port each was given."""
        return tuple(
            _url_of(socket.getsockname())
            for server in self._servers
            for socket in server.sockets)

    async def start(self) -> None:
        for url in self._configured_urls:
            host, port = _endpoint(url)
            self._servers.append(await asyncio.start_server(self._serve, host, port))

    async def aclose(self) -> None:
        """Stops listening, then closes every connection."""
        for server in self._servers:
            server.close()

        for connection in list(self._connections):
            connection.cancel()

        await asyncio.gather(*self._connections, return_exceptions=True)

        for server in self._servers:
            await server.wait_closed()

    async def __aenter__(self) -> AgentHost:
        await self.start()

        return self

    async def __aexit__(self, *exception_info: object) -> None:
        await self.aclose()

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        connection = _Connection(reader, writer)
        task = asyncio.current_task()
        self._connections.add(task)

        try:
            while True:
                request = await connection.read_request()

                if request is None:
                    break

                keep_alive = await self._respond(connection, request)

                if not keep_alive:
                    break

        except (ConnectionError, asyncio.IncompleteReadError):
            pass

        finally:
            self._connections.discard(task)
            writer.close()

            with suppress(Exception):
                await writer.wait_closed()

    async def _respond(self, connection: _Connection, request: HttpRequest) -> bool:
        """Answer one request; whether the connection can carry another.

        The scheme establishes who the request is before anything else runs, and the context
        holds them for the request's whole life, so the agent's principal callable, called
        deep inside the run, reads this request's user and never another's.
        """
        user = await self._authenticate_user(request)
        self._http_context_accessor.http_context = HttpContext(user=user)

        try:
            return await self._respond_to(connection, request, user)
        finally:
            self._http_context_accessor.http_context = None

    async def _authenticate_user(self, request: HttpRequest) -> ClaimsPrincipal:
        user = await self._authenticate(request) if self._authenticate is not None else None

        # No scheme, or a scheme with no result, is an anonymous user, never no user.
        return user if user is not None else ClaimsPrincipal()

    async def _respond_to(
            self,
            connection: _Connection,
            request: HttpRequest,
            user: ClaimsPrincipal) -> bool:

        # The front door, before the routes: no configured key means open (a laptop), one
        # configuration line means every agent route wants X-Api-Key (a deployment). The
        # heartbeat stays open either way: a probe cannot present a key and learns nothing.
        key_allowed = api_key_gate.allows(
            configured_key=self._api_key,
            presented_key=request.headers.get("x-api-key"),
            path=request.path)

        if not key_allowed:
            await connection.write_response(
                HTTPStatus.UNAUTHORIZED,
                body=b"missing or invalid X-Api-Key",
                keep_alive=request.keep_alive)

            return request.keep_alive

        # The second lock: with authentication configured, an agent route wants an
        # authenticated user, established by the scheme and handed to the agent as the
        # principal.
        identity_allowed = identity_gate.allows(
            self._authentication_configured,
            user_is_authenticated=user.identity is not None and user.identity.is_authenticated,
            path=request.path)

        if not identity_allowed:
            await connection.write_response(
                HTTPStatus.UNAUTHORIZED,
                body=b"an authenticated user is required",
                keep_alive=request.keep_alive)

            return request.keep_alive

        route = next(
            (route for route in _ROUTES
             if route.matches(request.path) and route.method == request.method),
            None)

        if route is None:
            await connection.write_response(HTTPStatus.NOT_FOUND, keep_alive=request.keep_alive)

            return request.keep_alive

        model = None

        if route.request_type is not None:
            model = wire.read_model(route.request_type, request.body.decode("utf-8"))
            errors = wire.required_field_errors(model)

            if errors:
                await _write_validation_problem(connection, request, errors)

                return request.keep_alive

        result = await route.action(self._get_agent, model, asyncio.Event())

        if isinstance(result, StreamResult):
            return await _write_stream_result(connection, request, result)

        await _write_object_result(connection, request, result)

        return request.keep_alive

    def _get_agent(self) -> Agent:
        if self._agent is None:
            self._agent = self._resolve_agent()

        return self._agent


async def _write_object_result(
        connection: _Connection,
        request: HttpRequest,
        result: ObjectResult) -> None:

    if isinstance(result.value, str):
        content_type = "text/plain; charset=utf-8"
        body = result.value
    else:
        content_type = "application/json; charset=utf-8"
        body = wire.write_json(result.value)

    await connection.write_response(
        result.status_code,
        headers=(("Content-Type", content_type),),
        body=body.encode("utf-8"),
        keep_alive=request.keep_alive)


async def _write_stream_result(
        connection: _Connection,
        request: HttpRequest,
        result: StreamResult) -> bool:
    """Write each piece of the body as it comes, flushed, as Response.WriteAsync and a flush do.

    Chunked on HTTP/1.1, as Kestrel frames a response whose length it cannot know; an HTTP/1.0
    caller cannot read chunks, so its response ends when the connection closes. A body that
    produced nothing is an empty response with its length, as Kestrel ends one that never
    started.
    """
    chunked = request.version == "HTTP/1.1"
    keep_alive = request.keep_alive and chunked
    headers = (("Content-Type", result.content_type),) if result.content_type else ()
    started = False

    async for piece in result.body:
        data = piece.encode("utf-8")

        if not data:
            continue

        if not started:
            framing = ("Transfer-Encoding", "chunked") if chunked else None
            await connection.write_head(result.status_code, headers, framing, keep_alive)
            started = True

        await connection.write_body_part(data, chunked=chunked)

    if not started:
        await connection.write_response(
            result.status_code,
            headers=headers,
            keep_alive=request.keep_alive)

        return request.keep_alive

    if chunked:
        await connection.write_body_part(b"", chunked=True)

    return keep_alive


async def _write_validation_problem(
        connection: _Connection,
        request: HttpRequest,
        errors: dict[str, list[str]]) -> None:
    """The 400 the C# host's [ApiController] answers a request that failed binding with: a
    ValidationProblemDetails naming every field that failed."""

    problem = {
        "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
        "title": "One or more validation errors occurred.",
        "status": HTTPStatus.BAD_REQUEST.value,
        "errors": errors,
        "traceId": _trace_id(),
    }

    await connection.write_response(
        HTTPStatus.BAD_REQUEST,
        headers=(("Content-Type", "application/problem+json; charset=utf-8"),),
        body=wire.write_json(problem).encode("utf-8"),
        keep_alive=request.keep_alive)


class _Connection:
    """One client connection: the bytes read so far and the writer to answer on."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader = reader
        self.writer = writer
        self.buffer = bytearray()

    async def read_request(self) -> HttpRequest | None:
        head = await self._read_head()

        if head is None:
            return None

        lines = head.decode("latin-1").split("\r\n")
        method, target, version = lines[0].split(" ")
        headers: dict[str, str] = {}

        for line in lines[1:]:
            name, _, value = line.partition(":")
            name = name.lower()
            value = value.strip(" \t")
            headers[name] = f"{headers[name]},{value}" if name in headers else value

        body = await self._read_exactly(int(headers.get("content-length", "0")))

        return HttpRequest(method, _path_of(target), version, headers, body)

    async def write_response(
            self,
            status: HTTPStatus,
            *,
            headers: Sequence[tuple[str, str]] = (),
            body: bytes = b"",
            keep_alive: bool) -> None:

        framing = ("Content-Length", str(len(body)))
        await self.write_head(status, headers, framing, keep_alive, body)

    async def write_head(
            self,
            status: HTTPStatus,
            headers: Sequence[tuple[str, str]],
            framing: tuple[str, str] | None,
            keep_alive: bool,
            body: bytes = b"") -> None:

        head = [f"HTTP/1.1 {status.value} {status.phrase}"]
        head.extend(f"{name}: {value}" for name, value in headers)
        head.append(f"Date: {formatdate(usegmt=True)}")

        if framing is not None:
            head.append(f"{framing[0]}: {framing[1]}")

        if not keep_alive:
            head.append("Connection: close")

        self.writer.write(("\r\n".join(head) + "\r\n\r\n").encode("latin-1") + body)
        await self.writer.drain()

    async def write_body_part(self, data: bytes, *, chunked: bool) -> None:
        """One piece of a body, flushed; on a chunked body an empty piece is the last chunk."""
        if chunked:
            data = f"{len(data):x}\r\n".encode("latin-1") + data + b"\r\n"

        self.writer.write(data)
        await self.writer.drain()

    async def _read_head(self) -> bytes | None:
        while True:
            end = self.buffer.find(b"\r\n\r\n")

            if end >= 0:
                head = bytes(self.buffer[:end])
                del self.buffer[:end + 4]

                return head

            if not await self._fill():
                if self.buffer:
                    raise asyncio.IncompleteReadError(bytes(self.buffer), None)

                return None

    async def _read_exactly(self, length: int) -> bytes:
        while len(self.buffer) < length:
            if not await self._fill():
                raise asyncio.IncompleteReadError(bytes(self.buffer), length)

        data = bytes(self.buffer[:length])
        del self.buffer[:length]

        return data

    async def _fill(self) -> bool:
        data = await self.reader.read(65536)
        self.buffer.extend(data)

        return bool(data)


def _path_of(target: str) -> str:
    """The request's path, percent-decoded as ASP.NET decodes it: all but an encoded slash."""
    path = target.split("?", 1)[0]

    return "".join(
        part if _PERCENT_ENCODED_SLASH.fullmatch(part) else urllib.parse.unquote(part)
        for part in _PERCENT_ENCODED_SLASH.split(path))


def _trace_id() -> str:
    """A W3C trace id, the shape ASP.NET stamps a problem with when no trace is running."""
    return f"00-{secrets.token_hex(16)}-{secrets.token_hex(8)}-00"


def _endpoint(url: str) -> tuple[str | None, int]:
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname

    # Kestrel reads * and + as every interface.
    return (None if host in ("*", "+") else host), (parts.port if parts.port is not None else 80)


def _url_of(address: tuple) -> str:
    host, port = address[0], address[1]

    return f"http://[{host}]:{port}" if ":" in host else f"http://{host}:{port}"
