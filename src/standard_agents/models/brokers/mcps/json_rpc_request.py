# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MISSING = object()


@dataclass(frozen=True)
class JsonRpcRequest:
    """A JSON-RPC 2.0 request to an MCP server.

    Params is None for parameterless methods such as tools/list, and the serializer omits it
    (WhenWritingNull) rather than sending "params": null, which some servers reject.

    Wire names follow JsonNamingPolicy.CamelCase, except "jsonrpc", which is pinned with
    [JsonPropertyName("jsonrpc")]; reads are case-insensitive.
    """

    json_rpc: str
    id: int | None
    method: str

    # Written by its runtime type, as an object-typed property is: a params DTO writes itself,
    # anything else is written as the JSON it already is.
    params: Any | None

    def to_json_dict(self) -> dict:
        values = {
            "jsonrpc": self.json_rpc,
            "id": self.id,
            "method": self.method,
            "params": (
                self.params.to_json_dict() if hasattr(self.params, "to_json_dict")
                else self.params),
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> JsonRpcRequest:
        """Read a request; params reads back as the raw JSON it arrived as (a JsonElement)."""
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to JsonRpcRequest.")

        request_id = _read_ignoring_case(data, "id")
        params = _read_ignoring_case(data, "params")

        return cls(
            json_rpc=_as_string(_read_ignoring_case(data, "jsonrpc")),
            id=None if request_id is _MISSING or request_id is None else _as_int32(request_id),
            method=_as_string(_read_ignoring_case(data, "method")),
            params=None if params is _MISSING else params)


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


def _as_int32(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and -2**31 <= value < 2**31:
        return value

    raise ValueError("The JSON value could not be converted to System.Int32.")
