# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import atexit
import copy
import functools
import importlib.metadata
import json
import os
import re
import signal
import subprocess
from collections import deque
from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Any, Protocol

from restfulsense.exceptions import HttpRequestException
from standard_agents.brokers.mcps import mcp_json
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool

_JSON_RPC_VERSION = "2.0"
_TOOLS_LIST_METHOD = "tools/list"
_TOOLS_CALL_METHOD = "tools/call"
_INITIALIZE_METHOD = "initialize"
_INITIALIZED_METHOD = "notifications/initialized"
_LATEST_PROTOCOL_VERSION = "2025-06-18"
_CLIENT_NAME = "Standard.Agents"
_OPEN_OBJECT_SCHEMA = "{}"
_PING_METHOD = "ping"
_METHOD_NOT_FOUND_CODE = -32601

# StreamReader.ReadLine ends a line at \r\n, \r or \n.
_LINE_BREAK = re.compile(r"\r\n|\r|\n")

# StreamReader has no line length limit; asyncio's default of 64 KiB would fail a large catalog.
_LINE_LIMIT = 2**31 - 1

_BYTE_ORDER_MARK = "﻿"


class ServerOutput(Protocol):
    """The server's standard output, as the broker reads it.

    asyncio.StreamReader's readline, which returns b"" (or "") at the end of the stream.
    """

    async def readline(self) -> bytes | str:
        ...


class ServerInput(Protocol):
    """The server's standard input, as the broker writes it.

    asyncio.StreamWriter's write and drain.
    """

    def write(self, data: bytes) -> None:
        ...

    async def drain(self) -> None:
        ...


class StdioMcpBroker(McpBroker):
    """An MCP server spoken to over its standard input and output.

    Pass server_output and server_input for streams already open, or pass command to start the
    server as a process (on first use, and again on the first use after it exits). A process the
    broker started is stopped, with every process it started, when the interpreter exits, as the
    C# stops it when the host exits; aclose(), or leaving an async with block, stops it sooner.
    """

    def __init__(
            self,
            server_output: ServerOutput | None = None,
            server_input: ServerInput | None = None,
            *,
            timeout_seconds: int,
            command: str | None = None,
            arguments: Iterable[str] | None = None,
            environment_variables: Mapping[str, str] | None = None,
            working_directory: str | None = None) -> None:

        self._connect: Callable[[], Awaitable[tuple[ServerOutput, ServerInput]]]

        if command is None:
            async def connect_to_streams() -> tuple[ServerOutput, ServerInput]:
                return server_output, server_input

            self._connect = connect_to_streams
        else:
            process_arguments = list(arguments)

            async def connect_to_process() -> tuple[ServerOutput, ServerInput]:
                server_process = await _start_server_process(
                    command,
                    process_arguments,
                    environment_variables,
                    working_directory)

                self._server_process = server_process
                self._stop_at_exit = functools.partial(_stop_server_process, server_process)
                atexit.register(self._stop_at_exit)

                return server_process.stdout, server_process.stdin

            self._connect = connect_to_process

        self._timeout_seconds = timeout_seconds
        self._exchange_lock = asyncio.Lock()
        self._server_output: ServerOutput | None = None
        self._server_input: ServerInput | None = None
        self._pending_lines: deque[str] = deque()
        self._is_start_of_output = True
        self._request_id = 0
        self._is_initialized = False
        self._server_process: asyncio.subprocess.Process | None = None
        self._stop_at_exit: Callable[[], None] | None = None

    async def aclose(self) -> None:
        """Stop the server process this broker started, and every process it started.

        The next use starts the server again. Streams handed to the broker are the caller's,
        and are left as they are.
        """
        async with self._exchange_lock:
            server_process = self._server_process

            if server_process is None:
                return

            atexit.unregister(self._stop_at_exit)
            self._server_process = None
            self._stop_at_exit = None
            self._is_initialized = False

            await asyncio.to_thread(_stop_server_process, server_process)
            server_process.stdin.close()
            await server_process.wait()

    async def call(self, name: str, arguments_json: str) -> str:
        parameters = {
            "name": name,
            "arguments": mcp_json.parse(arguments_json),
        }

        result = await self._request(_TOOLS_CALL_METHOD, parameters)
        content = _index(result, "content")
        contents = content if isinstance(content, list) else []
        text = "".join(_to_text(item) for item in contents)
        structured_content = _index(result, "structuredContent")

        return (
            mcp_json.to_json_string(structured_content)
            if not text and structured_content is not None
            else text)

    async def list_tools(self) -> list[McpTool]:
        tools: list[McpTool] = []
        visited_cursors: set[str] = set()
        cursor: str | None = None

        while True:
            parameters = None if cursor is None else {"cursor": cursor}
            page = await self._request(_TOOLS_LIST_METHOD, parameters)
            page_tools = _index(page, "tools")

            for tool in page_tools if isinstance(page_tools, list) else []:
                if tool is None:
                    raise TypeError("Object reference not set to an instance of an object.")

                name = _index(tool, "name")

                if name is None:
                    raise TypeError("Object reference not set to an instance of an object.")

                description = _get_string(_index(tool, "description"))
                input_schema = _index(tool, "inputSchema")

                tools.append(McpTool(
                    _get_string(name),
                    description if description is not None else "",
                    (mcp_json.to_json_string(input_schema) if input_schema is not None
                        else _OPEN_OBJECT_SCHEMA)))

            cursor = _get_string(_index(page, "nextCursor"))

            if not cursor or cursor in visited_cursors:
                break

            visited_cursors.add(cursor)

        return tools

    async def _request(self, method: str, parameters: Any) -> Any:
        async with self._exchange_lock:
            await self._ensure_initialized()
            answer = await self._exchange(method, parameters)
            error = answer.get("error")

            if error is not None:
                raise HttpRequestException(_get_string(_index(error, "message")))

            return answer.get("result")

    async def _ensure_initialized(self) -> None:
        if self._is_initialized:
            return

        server_output, self._server_input = await self._connect()

        # A new output is a new StreamReader: nothing buffered, its byte order mark unread.
        if server_output is not self._server_output:
            self._server_output = server_output
            self._pending_lines.clear()
            self._is_start_of_output = True

        initialize_parameters = {
            "protocolVersion": _LATEST_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {
                "name": _CLIENT_NAME,
                "version": _client_version(),
            },
        }

        answer = await self._exchange(_INITIALIZE_METHOD, initialize_parameters)
        error_code = _get_int(_index(answer.get("error"), "code"))

        if error_code is not None and error_code != _METHOD_NOT_FOUND_CODE:
            raise HttpRequestException(_get_string(_index(answer["error"], "message")))

        if error_code is None:
            await self._write({"jsonrpc": _JSON_RPC_VERSION, "method": _INITIALIZED_METHOD})

        self._is_initialized = True

    async def _exchange(self, method: str, parameters: Any) -> dict:
        self._request_id += 1
        request_id = self._request_id

        request: dict[str, Any] = {
            "jsonrpc": _JSON_RPC_VERSION,
            "id": request_id,
            "method": method,
        }

        if parameters is not None:
            request["params"] = parameters

        await self._write(request)

        # One timeout for the whole exchange, however many lines arrive before the answer.
        deadline = asyncio.get_running_loop().time() + self._timeout_seconds

        while True:
            line = await self._read_line(deadline)

            if line is None:
                raise self._disconnect()

            message = _to_message(line)

            if message is not None and "method" in message:
                await self._answer_server(message)

                continue

            if _is_answer_to(message, request_id):
                return message

    async def _read_line(self, deadline: float) -> str | None:
        """The next line as StreamReader.ReadLineAsync reads it: None at the end of the output.

        A line ends at \\r\\n, \\r or \\n, and no empty line follows a final line break.
        """
        while not self._pending_lines:
            remaining_seconds = deadline - asyncio.get_running_loop().time()

            try:
                chunk = await asyncio.wait_for(
                    self._server_output.readline(),
                    timeout=remaining_seconds)
            except asyncio.TimeoutError as timeout_error:
                raise TimeoutError(
                    "The MCP server did not answer within "
                    f"{self._timeout_seconds} seconds.") from timeout_error

            if not chunk:
                return None

            text = chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else chunk

            if self._is_start_of_output:
                self._is_start_of_output = False
                text = text[1:] if text.startswith(_BYTE_ORDER_MARK) else text

            lines = _LINE_BREAK.split(text)

            if not lines[-1]:
                lines.pop()

            self._pending_lines.extend(lines)

        return self._pending_lines.popleft()

    def _disconnect(self) -> HttpRequestException:
        self._is_initialized = False

        return HttpRequestException("The MCP server ended its output before answering.")

    async def _answer_server(self, server_message: dict) -> None:
        if server_message.get("id") is None:
            return

        answer: dict[str, Any] = {
            "jsonrpc": _JSON_RPC_VERSION,
            "id": copy.deepcopy(server_message["id"]),
        }

        if _get_string(server_message.get("method")) == _PING_METHOD:
            answer["result"] = {}
        else:
            answer["error"] = {
                "code": _METHOD_NOT_FOUND_CODE,
                "message": "The client does not offer this method.",
            }

        await self._write(answer)

    async def _write(self, message: dict) -> None:
        """One message per line: JSON never carries a raw line break, and the line ends with \\n."""
        self._server_input.write((mcp_json.to_json_string(message) + "\n").encode("utf-8"))
        await self._server_input.drain()


def _to_text(content: Any) -> str:
    content_type = _get_string(_index(content, "type"))

    if content_type == "text":
        text = _get_string(_index(content, "text"))

        return text if text is not None else ""

    if content_type == "resource":
        resource = _index(content, "resource")
        resource_text = _get_string(_index(resource, "text"))

        return (
            resource_text if resource_text is not None
            else f"[resource {_text(_get_string(_index(resource, 'uri')))}]")

    if content_type == "resource_link":
        name = _get_string(_index(content, "name"))
        uri = _get_string(_index(content, "uri"))

        return f"[resource_link {_text(name)}: {_text(uri)}]"

    return f"[{_text(content_type)} {_text(_get_string(_index(content, 'mimeType')))}]"


def _to_message(line: str) -> dict | None:
    try:
        message = mcp_json.parse(line)
    except json.JSONDecodeError:
        return None

    return message if isinstance(message, dict) else None


def _is_answer_to(message: dict | None, request_id: int) -> bool:
    """The answer's id must be a JSON integer that fits an int and equals the request's."""
    if message is None:
        return False

    answer_id = message.get("id")

    # A JSON true is not an id: bool is an int to isinstance.
    return (
        isinstance(answer_id, int)
        and not isinstance(answer_id, bool)
        and -2**31 <= answer_id < 2**31
        and answer_id == request_id)


def _index(node: Any, name: str) -> Any:
    """node?[name] on a JsonNode: null stays null, an object answers, anything else throws."""
    if node is None:
        return None

    if isinstance(node, dict):
        return node.get(name)

    raise TypeError(f"The node must be of type 'JsonObject' to read '{name}'.")


def _get_string(node: Any) -> str | None:
    """node?.GetValue<string>(): null stays null, a string answers, anything else throws."""
    if node is None or isinstance(node, str):
        return node

    raise TypeError("An element of type other than 'String' cannot be converted to 'String'.")


def _get_int(node: Any) -> int | None:
    """node?.GetValue<int>() on a JsonNode.

    Null stays null, an integer that fits an int answers, anything else throws.
    """
    if node is None:
        return None

    # A JSON true or false is not an integer: bool is an int to isinstance.
    if isinstance(node, int) and not isinstance(node, bool) and -2**31 <= node < 2**31:
        return int(node)

    raise TypeError("An element of this type cannot be converted to 'Int32'.")


def _text(value: str | None) -> str:
    """The value as C# string interpolation writes it: null as nothing."""
    return "" if value is None else value


async def _start_server_process(
        command: str,
        arguments: list[str],
        environment_variables: Mapping[str, str] | None,
        working_directory: str | None) -> asyncio.subprocess.Process:

    server_environment = dict(os.environ)

    for name, value in (environment_variables or {}).items():
        # ProcessStartInfo.Environment is case-insensitive on Windows: a name replaces any
        # spelling of itself.
        if os.name == "nt":
            spellings = [key for key in server_environment if key.upper() == name.upper()]

            for existing_name in spellings:
                del server_environment[existing_name]

        server_environment[name] = value

    server_process = await asyncio.create_subprocess_exec(
        _resolve_command(command),
        *arguments,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        # Standard error is dropped, every line of it, as the C# drains and discards it.
        stderr=asyncio.subprocess.DEVNULL,
        cwd=working_directory or None,
        env=server_environment,
        limit=_LINE_LIMIT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

    return server_process


def _stop_server_process(server_process: asyncio.subprocess.Process) -> None:
    """Process.Kill(entireProcessTree: true); a process that has already exited is left alone."""
    if server_process.returncode is not None:
        return

    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(server_process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            for process_id in [server_process.pid, *_descendants_of(server_process.pid)]:
                try:
                    os.kill(process_id, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    except OSError:
        pass


def _descendants_of(process_id: int) -> list[int]:
    parents: dict[int, list[int]] = {}

    try:
        entries = os.listdir("/proc")
    except OSError:
        return []

    for entry in entries:
        if not entry.isdigit():
            continue

        try:
            with open(f"/proc/{entry}/stat", encoding="utf-8") as stat_file:
                parent_id = int(stat_file.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            continue

        parents.setdefault(parent_id, []).append(int(entry))

    descendants: list[int] = []
    pending = list(parents.get(process_id, []))

    while pending:
        child_id = pending.pop()
        descendants.append(child_id)
        pending.extend(parents.get(child_id, []))

    return descendants


def _resolve_command(command: str) -> str:
    """The executable a command names.

    On Windows a bare name resolves through PATH and PATHEXT, so npx finds npx.cmd; a name with an
    extension, or any name elsewhere, is started as given.
    """
    if os.name != "nt" or _has_extension(command):
        return command

    directories = [
        directory for directory in os.environ.get("PATH", "").split(os.pathsep)
        if directory]

    extensions = [
        extension for extension in os.environ.get("PATHEXT", ".EXE;.CMD;.BAT").split(";")
        if extension]

    for directory in directories:
        for extension in extensions:
            candidate = os.path.join(directory, command + extension)

            if os.path.isfile(candidate):
                return candidate

    return command


def _has_extension(path: str) -> bool:
    """Path.HasExtension: a dot in the last segment that is not its final character."""
    last_segment = re.split(r"[\\/]", path)[-1]

    return "." in last_segment and not last_segment.endswith(".")


def _client_version() -> str:
    """The installed distribution's version (the assembly version in C#), empty when none."""
    try:
        return importlib.metadata.version("standard-agents")
    except importlib.metadata.PackageNotFoundError:
        return ""
