# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import http.client
import importlib.metadata
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import Message
from collections.abc import Awaitable, Callable
from typing import Any

from restfulsense.exceptions import HttpRequestException
from restfulsense.validation_service import read_as_string, validate_http_response
from standard_agents.brokers.mcps import mcp_json
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.models.brokers.mcps.initialize_params import ClientInfo, InitializeParams
from standard_agents.models.brokers.mcps.initialize_result import JsonRpcInitializeResponse
from standard_agents.models.brokers.mcps.json_rpc_request import JsonRpcRequest
from standard_agents.models.brokers.mcps.json_rpc_response import JsonRpcResponse
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.brokers.mcps.tool_call_content import ToolCallContent
from standard_agents.models.brokers.mcps.tool_call_params import ToolCallParams
from standard_agents.models.brokers.mcps.tool_list_params import ToolListParams
from standard_agents.models.brokers.mcps.tool_list_result import (
    JsonRpcToolListResponse,
    ToolListResult)

_JSON_MEDIA_TYPE = "application/json"
_EVENT_STREAM_MEDIA_TYPE = "text/event-stream"
_DATA_FIELD_PREFIX = "data:"
_JSON_RPC_VERSION = "2.0"
_TOOLS_CALL_METHOD = "tools/call"
_TOOLS_LIST_METHOD = "tools/list"
_INITIALIZE_METHOD = "initialize"
_INITIALIZED_METHOD = "notifications/initialized"
_LATEST_PROTOCOL_VERSION = "2025-06-18"
_CLIENT_NAME = "Standard.Agents"
_SESSION_ID_HEADER = "Mcp-Session-Id"
_PROTOCOL_VERSION_HEADER = "MCP-Protocol-Version"
_METHOD_NOT_FOUND_CODE = -32601
_OPEN_OBJECT_SCHEMA = "{}"

# StringContent(json, Encoding.UTF8, "application/json") sends the charset with the media type.
_REQUEST_CONTENT_TYPE = "application/json; charset=utf-8"

# StreamReader.ReadLine ends a line at \r\n, \r or \n.
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


@dataclass(frozen=True)
class _HttpResponse:
    status_code: int
    headers: Message
    body: bytes


class HttpMcpBroker(McpBroker):
    """An MCP server reached over Streamable HTTP.

    ``handler`` is the host's (F-23): a urllib OpenerDirector, the composition of handlers urllib
    sends through, which this broker never closes; without one, a default is built. A dynamic
    token is asked for on every request, because the one from composition time expires (OAuth).
    Static credentials ride the default headers; the provider, when present, wins over both.
    """

    def __init__(
            self,
            endpoint_url: str,
            relative_url: str,
            timeout_seconds: int,
            bearer_token: str | None = None,
            api_key: str | None = None,
            api_key_header: str = "X-Api-Key",
            bearer_token_provider: Callable[[], Awaitable[str]] | None = None,
            handler: urllib.request.OpenerDirector | None = None) -> None:

        # HttpClient.BaseAddress takes an absolute address only, and Timeout a positive one.
        if not urllib.parse.urlsplit(endpoint_url).scheme:
            raise ValueError("Invalid URI: The format of the URI could not be determined.")

        if timeout_seconds <= 0:
            raise ValueError("The timeout must be greater than zero.")

        if handler is None:
            # HttpClientHandler sends no User-Agent of its own, so this opener sends none either.
            handler = urllib.request.build_opener()
            handler.addheaders = []

        default_headers: dict[str, str] = {
            "Accept": f"{_JSON_MEDIA_TYPE}, {_EVENT_STREAM_MEDIA_TYPE}",
        }

        if bearer_token_provider is None and bearer_token:
            default_headers["Authorization"] = f"Bearer {bearer_token}"

        if api_key:
            default_headers[api_key_header] = api_key

        self._handler = handler
        self._endpoint_url = endpoint_url
        self._timeout_seconds = timeout_seconds
        self._default_headers = default_headers
        self._bearer_token_provider = bearer_token_provider
        self._relative_url = relative_url
        self._initialization_lock = asyncio.Lock()
        self._request_id = 0
        self._is_initialized = False
        self._session_id: str | None = None
        self._protocol_version: str | None = None

    async def call(self, name: str, arguments_json: str) -> str:
        await self._ensure_initialized()

        json_rpc_request = JsonRpcRequest(
            json_rpc=_JSON_RPC_VERSION,
            id=self._next_request_id(),
            method=_TOOLS_CALL_METHOD,
            params=ToolCallParams(
                name=name,
                arguments=mcp_json.parse(arguments_json)))

        json_rpc_response, response_json = await self._post(
            self._relative_url,
            json_rpc_request,
            JsonRpcResponse)

        return _to_text(json_rpc_response, response_json)

    async def list_tools(self) -> list[McpTool]:
        await self._ensure_initialized()

        tools: list[McpTool] = []
        visited_cursors: set[str] = set()
        cursor: str | None = None

        while True:
            page, page_json = await self._list_tools_page(cursor)
            entries = (page.tools if page is not None else None) or ()
            raw_entries = mcp_json.raw_items(mcp_json.raw_member(page_json, "tools")) or []

            for index, tool in enumerate(entries):
                input_schema = (
                    None if tool.input_schema is None
                    else mcp_json.raw_member(raw_entries[index], "inputSchema"))

                tools.append(McpTool(
                    tool.name,
                    tool.description if tool.description is not None else "",
                    input_schema if input_schema is not None else _OPEN_OBJECT_SCHEMA))

            cursor = page.next_cursor if page is not None else None

            if not cursor or cursor in visited_cursors:
                break

            visited_cursors.add(cursor)

        return tools

    async def _list_tools_page(
            self,
            cursor: str | None) -> tuple[ToolListResult | None, str | None]:
        """The page and the raw JSON of the page, which the schemas are read from verbatim."""
        json_rpc_request = JsonRpcRequest(
            json_rpc=_JSON_RPC_VERSION,
            id=self._next_request_id(),
            method=_TOOLS_LIST_METHOD,
            params=None if cursor is None else ToolListParams(cursor))

        json_rpc_response, response_json = await self._post(
            self._relative_url,
            json_rpc_request,
            JsonRpcToolListResponse)

        if json_rpc_response.error is not None:
            raise HttpRequestException(json_rpc_response.error.message)

        return json_rpc_response.result, mcp_json.raw_member(response_json, "result")

    async def _ensure_initialized(self) -> None:
        if self._is_initialized:
            return

        async with self._initialization_lock:
            if not self._is_initialized:
                await self._initialize()
                self._is_initialized = True

    async def _initialize(self) -> None:
        initialize_request = JsonRpcRequest(
            json_rpc=_JSON_RPC_VERSION,
            id=self._next_request_id(),
            method=_INITIALIZE_METHOD,
            params=InitializeParams(
                protocol_version=_LATEST_PROTOCOL_VERSION,
                capabilities={},
                client_info=ClientInfo(name=_CLIENT_NAME, version=_client_version())))

        deadline = self._start_deadline()

        initialize_http_response = await self._send(
            self._relative_url,
            initialize_request,
            deadline)

        initialize_response, _ = _read(initialize_http_response, JsonRpcInitializeResponse)

        if (initialize_response.error is not None
                and initialize_response.error.code == _METHOD_NOT_FOUND_CODE):
            return

        if initialize_response.error is not None:
            raise HttpRequestException(initialize_response.error.message)

        session_ids = initialize_http_response.headers.get_all(_SESSION_ID_HEADER)
        self._session_id = session_ids[0] if session_ids else None

        self._protocol_version = (
            initialize_response.result.protocol_version
            if initialize_response.result is not None else None)

        initialized_notification = JsonRpcRequest(
            json_rpc=_JSON_RPC_VERSION,
            id=None,
            method=_INITIALIZED_METHOD,
            params=None)

        await self._notify(self._relative_url, initialized_notification)

    async def _post(self, relative_url: str, content: Any, result_type: type) -> tuple[Any, str]:
        deadline = self._start_deadline()
        sent_session_id = self._session_id
        http_response = await self._send(relative_url, content, deadline)

        if _is_expired_session(http_response, sent_session_id):
            await self._restart_session(sent_session_id)
            retried_http_response = await self._send(relative_url, content, deadline)

            return _read(retried_http_response, result_type)

        return _read(http_response, result_type)

    async def _restart_session(self, expired_session_id: str) -> None:
        async with self._initialization_lock:
            if self._session_id == expired_session_id:
                self._session_id = None
                self._protocol_version = None
                await self._initialize()

    async def _notify(self, relative_url: str, content: Any) -> None:
        """Send a notification; the response is closed unread."""
        await self._send(relative_url, content, self._start_deadline(), read_body=False)

    async def _send(
            self,
            relative_url: str,
            content: Any,
            deadline: float,
            read_body: bool = True) -> _HttpResponse:

        remaining_seconds = deadline - asyncio.get_running_loop().time()

        try:
            return await asyncio.wait_for(
                self._send_until(relative_url, content, read_body, remaining_seconds),
                timeout=remaining_seconds)
        except asyncio.TimeoutError as timeout_error:
            raise TimeoutError(self._timeout_message()) from timeout_error

    async def _send_until(
            self,
            relative_url: str,
            content: Any,
            read_body: bool,
            remaining_seconds: float) -> _HttpResponse:

        request_json = mcp_json.to_json_string(content)
        headers = dict(self._default_headers)

        if self._session_id is not None:
            headers[_SESSION_ID_HEADER] = self._session_id

        if self._protocol_version is not None:
            headers[_PROTOCOL_VERSION_HEADER] = self._protocol_version

        if self._bearer_token_provider is not None:
            headers["Authorization"] = f"Bearer {await self._bearer_token_provider()}"

        request = urllib.request.Request(
            urllib.parse.urljoin(self._endpoint_url, relative_url),
            data=request_json.encode("utf-8"),
            method="POST")

        for name, value in headers.items():
            request.add_header(name, value)

        request.add_header("Content-Type", _REQUEST_CONTENT_TYPE)

        try:
            return await asyncio.to_thread(
                _exchange,
                self._handler,
                request,
                max(remaining_seconds, 0.001),
                read_body)

        except TimeoutError as timeout_error:
            raise TimeoutError(self._timeout_message()) from timeout_error

        except urllib.error.URLError as url_error:
            if isinstance(url_error.reason, TimeoutError):
                raise TimeoutError(self._timeout_message()) from url_error

            raise HttpRequestException(str(url_error.reason)) from url_error

        except (OSError, http.client.HTTPException) as transport_error:
            raise HttpRequestException(str(transport_error)) from transport_error

    def _next_request_id(self) -> int:
        self._request_id += 1

        return self._request_id

    def _start_deadline(self) -> float:
        return asyncio.get_running_loop().time() + self._timeout_seconds

    def _timeout_message(self) -> str:
        return (
            "The request was canceled due to the configured HttpClient.Timeout of "
            f"{self._timeout_seconds} seconds elapsing.")


def _exchange(
        handler: urllib.request.OpenerDirector,
        request: urllib.request.Request,
        timeout_seconds: float,
        read_body: bool) -> _HttpResponse:

    try:
        response = handler.open(request, timeout=timeout_seconds)
    except urllib.error.HTTPError as http_error:
        response = http_error

    with response:
        return _HttpResponse(
            status_code=response.code,
            headers=response.headers,
            body=response.read() if read_body else b"")


def _to_text(json_rpc_response: JsonRpcResponse, response_json: str) -> str:
    if json_rpc_response.error is not None:
        raise HttpRequestException(json_rpc_response.error.message)

    result = json_rpc_response.result
    contents = (result.content if result is not None else None) or ()
    text = "".join(_content_to_text(content) for content in contents)

    if not text and result is not None and result.structured_content is not None:
        return mcp_json.raw_member(
            mcp_json.raw_member(response_json, "result"),
            "structuredContent")

    return text


def _content_to_text(content: ToolCallContent) -> str:
    if content.type == "text":
        return content.text if content.text is not None else ""

    if content.type == "resource":
        resource_text = content.resource.text if content.resource is not None else None
        resource_uri = content.resource.uri if content.resource is not None else None

        return resource_text if resource_text is not None else f"[resource {_text(resource_uri)}]"

    if content.type == "resource_link":
        return f"[resource_link {_text(content.name)}: {_text(content.uri)}]"

    return f"[{_text(content.type)} {_text(content.mime_type)}]"


def _is_expired_session(http_response: _HttpResponse, sent_session_id: str | None) -> bool:
    return http_response.status_code == 404 and sent_session_id is not None


def _read(http_response: _HttpResponse, result_type: type) -> tuple[Any, str]:
    """The model and the JSON it was read from.

    As RESTFulSense's ReadAsync: the status is validated (reading the whole body), then the body,
    or the event that answers inside an event stream, is deserialized.
    """
    content_type = http_response.headers.get("Content-Type")
    content = read_as_string(http_response.body, content_type)
    validate_http_response(http_response.status_code, content_type, content)

    response_json = (
        _read_response_from_event_stream(http_response.body) if _is_event_stream(content_type)
        else content)

    parsed = mcp_json.parse(response_json)

    return (None if parsed is None else result_type.from_json_dict(parsed)), response_json


def _is_event_stream(content_type: str | None) -> bool:
    return (
        content_type is not None
        and content_type.split(";")[0].strip() == _EVENT_STREAM_MEDIA_TYPE)


def _read_response_from_event_stream(body: bytes) -> str:
    """The data of the event that answers, read as a StreamReader over the body reads it.

    UTF-8 unless a byte order mark says otherwise, whatever the charset says.
    """
    event_data: list[str] = []

    for line in _read_lines(read_as_string(body, None)):
        if line.startswith(_DATA_FIELD_PREFIX):
            event_data.append(_to_field_value(line) + os.linesep)

            continue

        if not line and _is_response("".join(event_data)):
            return "".join(event_data)

        if not line:
            event_data.clear()

    if _is_response("".join(event_data)):
        return "".join(event_data)

    raise HttpRequestException("The MCP server closed its event stream without a response.")


def _read_lines(text: str) -> list[str]:
    """The lines StreamReader.ReadLine yields: ended by \\r\\n, \\r or \\n.

    ReadLine yields no empty line after a final line break, nor for an empty stream, which
    str.splitlines does not match (it also breaks on \\v, \\f, \\x1c..\\x1e, \\x85 and more).
    """
    lines = _LINE_BREAK.split(text)

    if not lines[-1]:
        lines.pop()

    return lines


def _to_field_value(line: str) -> str:
    value = line[len(_DATA_FIELD_PREFIX):]

    return value[1:] if value.startswith(" ") else value


def _is_response(event_data: str) -> bool:
    if not event_data or event_data.isspace():
        return False

    message = mcp_json.parse(event_data)

    return isinstance(message, dict) and ("result" in message or "error" in message)


def _text(value: str | None) -> str:
    """The value as C# string interpolation writes it: null as nothing."""
    return "" if value is None else value


def _client_version() -> str:
    """The installed distribution's version (the assembly version in C#), empty when none."""
    try:
        return importlib.metadata.version("standard-agents")
    except importlib.metadata.PackageNotFoundError:
        return ""
