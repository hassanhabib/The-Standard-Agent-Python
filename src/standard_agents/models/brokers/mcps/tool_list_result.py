# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""What an MCP tools/list request returns.

Wire names follow JsonNamingPolicy.CamelCase; reads are case-insensitive and null values are
omitted on write (WhenWritingNull), as the HttpMcpBroker's serializer options leave them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from standard_agents.models.brokers.mcps.json_rpc_error import JsonRpcError

_MISSING = object()


@dataclass(frozen=True)
class ToolListEntry:
    """One tool in a tools/list page.

    The schema rides as the raw JSON it arrived as: the broker hands it on as text and never
    interprets it, so a server's own vocabulary reaches the model unchanged.
    """

    # None when the server sent no name: the deserializer leaves a string null.
    name: str | None
    description: str | None

    # The parsed JSON it arrived as (a JsonElement?); None when absent or null.
    input_schema: Any | None

    def to_json_dict(self) -> dict:
        values = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> ToolListEntry:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ToolListEntry.")

        input_schema = _read_ignoring_case(data, "inputSchema")

        return cls(
            name=_as_string(_read_ignoring_case(data, "name")),
            description=_as_string(_read_ignoring_case(data, "description")),
            input_schema=None if input_schema is _MISSING else input_schema)


@dataclass(frozen=True)
class ToolListResult:
    # None when the server sent none, and an entry is None where the server sent null.
    tools: tuple[ToolListEntry | None, ...] | None
    next_cursor: str | None

    def to_json_dict(self) -> dict:
        values = {
            "tools": (
                None if self.tools is None
                else [
                    None if tool is None else tool.to_json_dict()
                    for tool in self.tools]),
            "nextCursor": self.next_cursor,
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> ToolListResult:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ToolListResult.")

        tools = _read_ignoring_case(data, "tools")

        if tools is _MISSING or tools is None:
            parsed_tools = None
        elif isinstance(tools, list):
            parsed_tools = tuple(
                None if tool is None else ToolListEntry.from_json_dict(tool)
                for tool in tools)
        else:
            raise ValueError(
                "The JSON value could not be converted to IReadOnlyList<ToolListEntry>.")

        return cls(
            tools=parsed_tools,
            next_cursor=_as_string(_read_ignoring_case(data, "nextCursor")))


@dataclass(frozen=True)
class JsonRpcToolListResponse:
    result: ToolListResult | None
    error: JsonRpcError | None

    def to_json_dict(self) -> dict:
        values = {
            "result": None if self.result is None else self.result.to_json_dict(),
            "error": None if self.error is None else self.error.to_json_dict(),
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> JsonRpcToolListResponse:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to JsonRpcToolListResponse.")

        result = _read_ignoring_case(data, "result")
        error = _read_ignoring_case(data, "error")

        return cls(
            result=(
                None if result is _MISSING or result is None
                else ToolListResult.from_json_dict(result)),
            error=(
                None if error is _MISSING or error is None
                else JsonRpcError.from_json_dict(error)))


def _read_ignoring_case(data: dict, name: str) -> Any:
    """Read a property the way PropertyNameCaseInsensitive does.

    Every key that matches the name ignoring case is read, and the last one wins.
    """
    found = _MISSING

    for key, value in data.items():
        if key.lower() == name.lower():
            found = value

    return found


def _as_string(value: Any) -> str | None:
    """Read a JSON string, reading an absent or null value as None.

    An absent constructor parameter is default(string), which is null.
    """
    if value is _MISSING or value is None:
        return None

    if isinstance(value, str):
        return value

    raise ValueError("The JSON value could not be converted to System.String.")
