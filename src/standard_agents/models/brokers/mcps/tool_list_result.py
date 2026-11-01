# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from standard_agents.models.brokers.mcps.json_rpc_error import JsonRpcError

_MISSING = object()


# The schema rides as the raw JSON it arrived as: the broker hands it on as text and never
# interprets it, so a server's own vocabulary reaches the model unchanged.
#
# Wire names follow JsonNamingPolicy.CamelCase; reads are case-insensitive and null values are
# omitted on write (WhenWritingNull), as the HttpMcpBroker's serializer options leave them.
@dataclass(frozen=True)
class ToolListEntry:
    name: str
    description: str | None

    # A JsonElement? in C#: kept as the parsed JSON it arrived as; None when absent or null.
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

        input_schema = _read(data, "inputSchema")

        return cls(
            name=_as_string(_read(data, "name")),
            description=_as_string(_read(data, "description")),
            input_schema=None if input_schema is _MISSING else input_schema)


@dataclass(frozen=True)
class ToolListResult:
    tools: tuple[ToolListEntry, ...]
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

        tools = _read(data, "tools")

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
            next_cursor=_as_string(_read(data, "nextCursor")))


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

        result = _read(data, "result")
        error = _read(data, "error")

        return cls(
            result=(
                None if result is _MISSING or result is None
                else ToolListResult.from_json_dict(result)),
            error=(
                None if error is _MISSING or error is None
                else JsonRpcError.from_json_dict(error)))


# PropertyNameCaseInsensitive: every key matching ignoring case is read, the last one wins.
def _read(data: dict, name: str) -> Any:
    found = _MISSING

    for key, value in data.items():
        if key.lower() == name.lower():
            found = value

    return found


# An absent constructor parameter is default(string), which is null.
def _as_string(value: Any) -> str | None:
    if value is _MISSING or value is None:
        return None

    if isinstance(value, str):
        return value

    raise ValueError("The JSON value could not be converted to System.String.")
