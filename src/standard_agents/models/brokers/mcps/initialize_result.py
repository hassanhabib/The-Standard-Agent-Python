# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""What an MCP initialize request returns.

Wire names follow JsonNamingPolicy.CamelCase; reads are case-insensitive and null values are
omitted on write (WhenWritingNull), as the HttpMcpBroker's serializer options leave them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from standard_agents.models.brokers.mcps.json_rpc_error import JsonRpcError

_MISSING = object()


@dataclass(frozen=True)
class InitializeResult:
    protocol_version: str | None

    def to_json_dict(self) -> dict:
        values = {
            "protocolVersion": self.protocol_version,
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> InitializeResult:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to InitializeResult.")

        return cls(protocol_version=_as_string(_read_ignoring_case(data, "protocolVersion")))


@dataclass(frozen=True)
class JsonRpcInitializeResponse:
    result: InitializeResult | None
    error: JsonRpcError | None

    def to_json_dict(self) -> dict:
        values = {
            "result": None if self.result is None else self.result.to_json_dict(),
            "error": None if self.error is None else self.error.to_json_dict(),
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> JsonRpcInitializeResponse:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to JsonRpcInitializeResponse.")

        result = _read_ignoring_case(data, "result")
        error = _read_ignoring_case(data, "error")

        return cls(
            result=(
                None if result is _MISSING or result is None
                else InitializeResult.from_json_dict(result)),
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
