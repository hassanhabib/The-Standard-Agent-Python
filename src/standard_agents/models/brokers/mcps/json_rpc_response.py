# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from standard_agents.models.brokers.mcps.json_rpc_error import JsonRpcError
from standard_agents.models.brokers.mcps.tool_call_result import ToolCallResult

_MISSING = object()


@dataclass(frozen=True)
class JsonRpcResponse:
    """A JSON-RPC response to tools/call: its result or its error.

    Wire names follow JsonNamingPolicy.CamelCase; reads are case-insensitive and null values are
    omitted on write (WhenWritingNull), as the HttpMcpBroker's serializer options leave them.
    """

    result: ToolCallResult | None
    error: JsonRpcError | None

    def to_json_dict(self) -> dict:
        values = {
            "result": None if self.result is None else self.result.to_json_dict(),
            "error": None if self.error is None else self.error.to_json_dict(),
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> JsonRpcResponse:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to JsonRpcResponse.")

        result = _read_ignoring_case(data, "result")
        error = _read_ignoring_case(data, "error")

        return cls(
            result=(
                None if result is _MISSING or result is None
                else ToolCallResult.from_json_dict(result)),
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
