# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The host's HTTP/1.1 server, on asyncio streams and nothing else.

Written for this host only: it reads a request, routes it to a controller by method and path,
binds the JSON body into the controller's model, and writes back what the controller answered,
as ASP.NET and Kestrel write it. Connections stay open between requests unless the caller asks
to close (HTTP/1.1 keep-alive); a request the server cannot read is answered and the connection
closed.
"""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import urllib.parse
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import aclosing, suppress
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

_LOGGER = logging.getLogger("standard_agents.host")

# Kestrel's defaults.
_MAX_REQUEST_LINE_BYTES = 8 * 1024
_MAX_REQUEST_HEADERS_BYTES = 32 * 1024
_MAX_REQUEST_BODY_BYTES = 30_000_000
_SHUTDOWN_TIMEOUT_SECONDS = 30.0

_PERCENT_ENCODED_SLASH = re.compile(r"(%2[Ff])")
_TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
_JSON_MEDIA_TYPE = re.compile(r"(application|text)/json|application/[^/;]+\+json")


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


class _MalformedRequest(Exception):
    """A request the server cannot read, and the status Kestrel answers it with."""

    def __init__(self, status: HTTPStatus) -> None:
        super().__init__(status.phrase)
        self.status = status


class _BindingFailure(Exception):
    """A body the route's model cannot be bound from, answered before the controller runs."""

    def __init__(self, status: HTTPStatus, errors: dict[str, list[str]] | None = None) -> None:
        super().__init__(status.phrase)
        self.status = status
        self.errors = errors


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
        self._connections: dict[asyncio.Task, _Connection] = {}
        self._closing = False

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
        """Stops listening, lets requests in flight finish, then closes the agent.

        Idle connections close at once; a request in flight gets the 30 seconds Kestrel gives
        it before its connection is closed under it. The agent is the host's because the host
        resolved it, as the C# container disposes the singletons it created: a StandardAgent
        stops the MCP server processes it started. An agent that offers no aclose has nothing
        to stop.
        """
        self._closing = True

        for server in self._servers:
            server.close()

        for task, connection in list(self._connections.items()):
            if not connection.busy:
                task.cancel()

        if self._connections:
            _, unfinished = await asyncio.wait(
                list(self._connections),
                timeout=_SHUTDOWN_TIMEOUT_SECONDS)

            for task in unfinished:
                task.cancel()

            await asyncio.gather(*unfinished, return_exceptions=True)

        for server in self._servers:
            await server.wait_closed()

        close_agent = getattr(self._agent, "aclose", None)
        self._agent = None

        if close_agent is not None:
            await close_agent()

    async def __aenter__(self) -> AgentHost:
        await self.start()

        return self

    async def __aexit__(self, *exception_info: object) -> None:
        await self.aclose()

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        connection = _Connection(reader, writer)
        task = asyncio.current_task()
        self._connections[task] = connection

        try:
            while not self._closing:
                try:
                    request = await connection.read_request()
                except _MalformedRequest as malformed:
                    await connection.write_response(malformed.status, keep_alive=False)

                    break

                if request is None:
                    break

                connection.busy = True
                keep_alive = await self._respond(connection, request)
                connection.busy = False

                if not keep_alive:
                    break

        except (ConnectionError, asyncio.IncompleteReadError):
            pass

        finally:
            del self._connections[task]
            writer.close()

            with suppress(Exception):
                await writer.wait_closed()

    async def _respond(self, connection: _Connection, request: HttpRequest) -> bool:
        """Answer one request; whether the connection can carry another.

        The scheme establishes who the request is before anything else runs, and the context
        holds them for the request's whole life, so the agent's principal callable, called
        deep inside the run, reads this request's user and never another's.
        """
        try:
            user = await self._authenticate_user(request)
            self._http_context_accessor.http_context = HttpContext(user=user)

            return await self._respond_to(connection, request, user)

        except ConnectionError:
            raise

        # A failure before anything was written is a 500 with no body, as ASP.NET answers
        # outside Development; a failure after the response started can only cut the
        # connection, so the caller cannot mistake half an answer for a whole one.
        except Exception:
            _LOGGER.exception("An unhandled exception has occurred while executing the request.")

            if connection.started:
                connection.abort()

                return False

            await connection.write_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                keep_alive=request.keep_alive)

            return request.keep_alive

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

        routes = [route for route in _ROUTES if route.matches(request.path)]
        route = next((route for route in routes if route.method == request.method), None)

        if route is None:
            return await _write_no_route(connection, request, routes)

        try:
            model = _bind(route.request_type, request)
        except _BindingFailure as failure:
            await _write_problem(connection, request, failure.status, failure.errors)

            return request.keep_alive

        return await self._run_action(connection, request, route, model)

    async def _run_action(
            self,
            connection: _Connection,
            request: HttpRequest,
            route: _Route,
            model: Any) -> bool:
        """Run the controller and write what it answered, watching for the caller leaving.

        The caller closing the connection sets the request's cancellation, which stops the run
        at its next turn boundary (HttpContext.RequestAborted in the C# host).
        """
        cancellation = asyncio.Event()
        watcher = asyncio.ensure_future(connection.wait_for_disconnect())
        watcher.add_done_callback(_setting(cancellation))

        try:
            result = await route.action(self._get_agent, model, cancellation)

            if isinstance(result, StreamResult):
                return await _write_stream_result(connection, request, result)

            await _write_object_result(connection, request, result)

            return request.keep_alive

        finally:
            watcher.cancel()

    def _get_agent(self) -> Agent:
        if self._agent is None:
            self._agent = self._resolve_agent()

        return self._agent


def _setting(cancellation: asyncio.Event) -> Callable[[asyncio.Future], None]:
    """Set the request's cancellation when the watch on its connection ends by itself."""

    def set_cancellation(watcher: asyncio.Future) -> None:
        if watcher.cancelled():
            return

        # Read, so a connection reset is not reported as an exception nobody retrieved.
        watcher.exception()
        cancellation.set()

    return set_cancellation


def _bind(request_type: type | None, request: HttpRequest) -> Any:
    """The route's model from the body, as [ApiController] binds [FromBody].

    A body that is not JSON is 415; a body that is empty, unreadable or JSON null, or a model
    with a null where its contract does not allow one, is a 400 naming what failed.
    """
    if request_type is None:
        return None

    media_type, _, parameters = request.headers.get("content-type", "").partition(";")

    if not _JSON_MEDIA_TYPE.fullmatch(media_type.strip().lower()):
        raise _BindingFailure(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    request_required = {"request": ["The request field is required."]}

    if not request.body:
        raise _BindingFailure(
            HTTPStatus.BAD_REQUEST,
            {"": ["A non-empty request body is required."], **request_required})

    try:
        model = wire.read_model(request_type, _decode(request.body, parameters))
    except wire.JsonReadError as error:
        raise _BindingFailure(
            HTTPStatus.BAD_REQUEST,
            {error.path: [error.message], **request_required}) from error

    if model is None:
        raise _BindingFailure(HTTPStatus.BAD_REQUEST, request_required)

    errors = wire.required_field_errors(model)

    if errors:
        raise _BindingFailure(HTTPStatus.BAD_REQUEST, errors)

    return model


def _decode(body: bytes, content_type_parameters: str) -> str:
    charset = "utf-8"

    for parameter in content_type_parameters.split(";"):
        name, _, value = parameter.partition("=")

        if name.strip().lower() == "charset" and value.strip():
            charset = value.strip().strip('"')

    try:
        return body.decode(charset).removeprefix("﻿")
    except LookupError as error:
        raise _BindingFailure(HTTPStatus.UNSUPPORTED_MEDIA_TYPE) from error
    except UnicodeDecodeError as error:
        raise wire.JsonReadError("$", f"{error}. Path: $.") from error


async def _write_no_route(
        connection: _Connection,
        request: HttpRequest,
        routes_on_path: list[_Route]) -> bool:
    """404 when nothing is at the path; 405 naming what is when only the method is wrong."""
    if not routes_on_path:
        await connection.write_response(HTTPStatus.NOT_FOUND, keep_alive=request.keep_alive)

        return request.keep_alive

    allowed = ", ".join(route.method for route in routes_on_path)

    await connection.write_response(
        HTTPStatus.METHOD_NOT_ALLOWED,
        headers=(("Allow", allowed),),
        keep_alive=request.keep_alive)

    return request.keep_alive


async def _write_problem(
        connection: _Connection,
        request: HttpRequest,
        status: HTTPStatus,
        errors: dict[str, list[str]] | None) -> None:
    """The problem [ApiController] answers a request that failed binding with: a
    ValidationProblemDetails naming every field that failed, or a ProblemDetails for a body
    that is not JSON at all."""
    if errors is None:
        problem = {
            "type": "https://tools.ietf.org/html/rfc9110#section-15.5.16",
            "title": status.phrase,
            "status": status.value,
            "traceId": _trace_id(),
        }
    else:
        problem = {
            "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
            "title": "One or more validation errors occurred.",
            "status": status.value,
            "errors": errors,
            "traceId": _trace_id(),
        }

    await connection.write_response(
        status,
        headers=(("Content-Type", "application/problem+json; charset=utf-8"),),
        body=wire.write_json(problem).encode("utf-8"),
        keep_alive=request.keep_alive)


async def _write_object_result(
        connection: _Connection,
        request: HttpRequest,
        result: ObjectResult) -> None:
    """A value in the format ASP.NET's output formatters choose: a string as text, unless the
    caller's Accept asks for JSON before text, and anything else as JSON."""
    if isinstance(result.value, str) and not _accepts_json_before_text(request):
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

    async with aclosing(result.body) as body:
        async for piece in body:
            data = piece.encode("utf-8")

            if not data:
                continue

            if not connection.started:
                framing = ("Transfer-Encoding", "chunked") if chunked else None
                await connection.write_head(result.status_code, headers, framing, keep_alive)

            await connection.write_body_part(data, chunked=chunked)

    if not connection.started:
        await connection.write_response(
            result.status_code,
            headers=headers,
            keep_alive=request.keep_alive)

        return request.keep_alive

    if chunked:
        await connection.write_body_part(b"", chunked=True)

    return keep_alive


def _accepts_json_before_text(request: HttpRequest) -> bool:
    """Whether content negotiation picks JSON over text for a string.

    ASP.NET ignores an Accept that names */* (a browser's), and otherwise tries the media
    types in quality order: the string formatter takes text/*, the JSON formatter takes JSON.
    """
    ranges = []

    for position, accepted in enumerate(request.headers.get("accept", "").split(",")):
        media_type, *parameters = (part.strip().lower() for part in accepted.split(";"))
        quality = 1.0

        for parameter in parameters:
            name, _, value = parameter.partition("=")

            if name.strip() == "q":
                with suppress(ValueError):
                    quality = float(value)

        if media_type:
            ranges.append((-quality, position, media_type))

    if any(media_type == "*/*" for _, _, media_type in ranges):
        return False

    for _, _, media_type in sorted(ranges):
        if media_type in ("text/plain", "text/*"):
            return False

        if media_type in ("application/*", "text/json") or _JSON_MEDIA_TYPE.fullmatch(media_type):
            return True

    return False


class _Connection:
    """One client connection: the bytes read so far and the writer to answer on."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader = reader
        self.writer = writer
        self.buffer = bytearray()
        self.busy = False
        self.started = False
        self.eof = False

    async def read_request(self) -> HttpRequest | None:
        head = await self._read_head()

        if head is None:
            return None

        method, target, version, headers = _parse_head(head)
        body = await self._read_body(version, headers)

        return HttpRequest(method, _path_of(target), version, headers, body)

    async def wait_for_disconnect(self) -> None:
        """Return when the caller closes the connection; keep anything it pipelined."""
        while not self.eof:
            if len(self.buffer) > _MAX_REQUEST_HEADERS_BYTES:
                await asyncio.Event().wait()

            await self._fill()

    async def write_response(
            self,
            status: HTTPStatus,
            *,
            headers: Sequence[tuple[str, str]] = (),
            body: bytes = b"",
            keep_alive: bool) -> None:

        framing = ("Content-Length", str(len(body)))
        await self.write_head(status, headers, framing, keep_alive, body)
        self.started = False

    async def write_head(
            self,
            status: HTTPStatus,
            headers: Sequence[tuple[str, str]],
            framing: tuple[str, str] | None,
            keep_alive: bool,
            body: bytes = b"") -> None:

        head = [f"HTTP/1.1 {status.value} {HTTPStatus(status).phrase}"]
        head.extend(f"{name}: {value}" for name, value in headers)
        head.append(f"Date: {formatdate(usegmt=True)}")

        if framing is not None:
            head.append(f"{framing[0]}: {framing[1]}")

        if not keep_alive:
            head.append("Connection: close")

        self.started = True
        self.writer.write(("\r\n".join(head) + "\r\n\r\n").encode("latin-1") + body)
        await self.writer.drain()

    async def write_body_part(self, data: bytes, *, chunked: bool) -> None:
        """One piece of a body, flushed; on a chunked body an empty piece is the last chunk."""
        if chunked:
            data = f"{len(data):x}\r\n".encode("latin-1") + data + b"\r\n"

        self.writer.write(data)
        await self.writer.drain()

        if chunked and data == b"0\r\n\r\n":
            self.started = False

    def abort(self) -> None:
        self.writer.transport.abort()

    async def _read_head(self) -> bytes | None:
        while True:
            # Blank lines before a request line are allowed, and skipped.
            while self.buffer.startswith(b"\r\n"):
                del self.buffer[:2]

            end = self.buffer.find(b"\r\n\r\n")

            if end >= 0:
                if end > _MAX_REQUEST_HEADERS_BYTES + _MAX_REQUEST_LINE_BYTES:
                    raise _MalformedRequest(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE)

                head = bytes(self.buffer[:end])
                del self.buffer[:end + 4]

                return head

            first_line_end = self.buffer.find(b"\r\n")
            request_line_length = len(self.buffer) if first_line_end < 0 else first_line_end

            if request_line_length > _MAX_REQUEST_LINE_BYTES:
                raise _MalformedRequest(HTTPStatus.REQUEST_URI_TOO_LONG)

            if len(self.buffer) > _MAX_REQUEST_HEADERS_BYTES + _MAX_REQUEST_LINE_BYTES:
                raise _MalformedRequest(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE)

            if not await self._fill():
                if self.buffer:
                    raise _MalformedRequest(HTTPStatus.BAD_REQUEST)

                return None

    async def _read_body(self, version: str, headers: dict[str, str]) -> bytes:
        transfer_encoding = headers.get("transfer-encoding")
        content_length = headers.get("content-length")

        if transfer_encoding is not None:
            codings = [coding.strip().lower() for coding in transfer_encoding.split(",")]

            if content_length is not None or codings[-1] != "chunked" or version == "HTTP/1.0":
                raise _MalformedRequest(HTTPStatus.BAD_REQUEST)

            await self._continue_if_expected(version, headers)

            return await self._read_chunked_body()

        length = _content_length(content_length)

        if length > _MAX_REQUEST_BODY_BYTES:
            raise _MalformedRequest(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)

        if length:
            await self._continue_if_expected(version, headers)

        return await self._read_exactly(length)

    async def _continue_if_expected(self, version: str, headers: dict[str, str]) -> None:
        if version == "HTTP/1.1" and headers.get("expect", "").lower() == "100-continue":
            self.writer.write(b"HTTP/1.1 100 Continue\r\n\r\n")
            await self.writer.drain()

    async def _read_chunked_body(self) -> bytes:
        body = bytearray()

        while True:
            size_line = (await self._read_line()).split(b";", 1)[0].strip()

            if not re.fullmatch(rb"[0-9A-Fa-f]{1,16}", size_line):
                raise _MalformedRequest(HTTPStatus.BAD_REQUEST)

            size = int(size_line, 16)

            if size == 0:
                while await self._read_line():
                    pass

                return bytes(body)

            if len(body) + size > _MAX_REQUEST_BODY_BYTES:
                raise _MalformedRequest(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)

            body.extend(await self._read_exactly(size))

            if await self._read_exactly(2) != b"\r\n":
                raise _MalformedRequest(HTTPStatus.BAD_REQUEST)

    async def _read_line(self) -> bytes:
        while True:
            end = self.buffer.find(b"\r\n")

            if end >= 0:
                line = bytes(self.buffer[:end])
                del self.buffer[:end + 2]

                return line

            if len(self.buffer) > _MAX_REQUEST_HEADERS_BYTES:
                raise _MalformedRequest(HTTPStatus.BAD_REQUEST)

            if not await self._fill():
                raise asyncio.IncompleteReadError(bytes(self.buffer), None)

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
        self.eof = not data

        return bool(data)


def _parse_head(head: bytes) -> tuple[str, str, str, dict[str, str]]:
    """The request line and the headers, refused as Kestrel refuses what it cannot read."""
    lines = head.split(b"\r\n")
    request_line = lines[0].split(b" ")

    if len(request_line) != 3:
        raise _MalformedRequest(HTTPStatus.BAD_REQUEST)

    method, target, version = (part.decode("latin-1") for part in request_line)

    if not _TOKEN.fullmatch(method) or not (
            target.startswith("/") or target.lower().startswith(("http://", "https://"))):
        raise _MalformedRequest(HTTPStatus.BAD_REQUEST)

    if version not in ("HTTP/1.1", "HTTP/1.0"):
        raise _MalformedRequest(
            HTTPStatus.HTTP_VERSION_NOT_SUPPORTED if re.fullmatch(r"HTTP/\d\.\d", version)
            else HTTPStatus.BAD_REQUEST)

    headers: dict[str, str] = {}

    for line in lines[1:]:
        name, separator, value = line.decode("latin-1").partition(":")

        # A folded line (leading white space) and a name with white space are both refused.
        if not separator or not _TOKEN.fullmatch(name):
            raise _MalformedRequest(HTTPStatus.BAD_REQUEST)

        name = name.lower()
        value = value.strip(" \t")
        headers[name] = f"{headers[name]},{value}" if name in headers else value

    if version == "HTTP/1.1" and "host" not in headers:
        raise _MalformedRequest(HTTPStatus.BAD_REQUEST)

    return method, _origin_form(target), version, headers


def _origin_form(target: str) -> str:
    """The path and query of a target, whether it came as /path or as http://host/path."""
    if target.startswith("/"):
        return target

    parts = urllib.parse.urlsplit(target)

    return (parts.path or "/") + (f"?{parts.query}" if parts.query else "")


def _content_length(value: str | None) -> int:
    if value is None:
        return 0

    lengths = {length.strip() for length in value.split(",")}

    if len(lengths) != 1 or not all(length.isdigit() and length.isascii() for length in lengths):
        raise _MalformedRequest(HTTPStatus.BAD_REQUEST)

    return int(lengths.pop())


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

    if parts.scheme.lower() != "http":
        raise ValueError(f"{url}: this host serves http only; put TLS in front of it.")

    host = parts.hostname

    # Kestrel reads * and + as every interface.
    return (None if host in ("*", "+") else host), (parts.port if parts.port is not None else 80)


def _url_of(address: tuple) -> str:
    host, port = address[0], address[1]

    return f"http://[{host}]:{port}" if ":" in host else f"http://{host}:{port}"
