# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MISSING = object()


# Params is None for parameterless methods such as tools/list, and the serializer omits it
# (WhenWritingNull) rather than sending "params": null, which some servers reject.
#
# Wire names follow JsonNamingPolicy.CamelCase, except "jsonrpc", which the C# record pins
# with [JsonPropertyName("jsonrpc")]; reads are case-insensitive.
@dataclass(frozen=True)
class JsonRpcRequest:
    json_rpc: str
    id: int | None
    method: str

    # Typed object in C#, so it is written by its runtime type: a params DTO writes itself,
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

    # An object property reads back as raw JSON (a JsonElement in C#).
    @classmethod
    def from_json_dict(cls, data: dict) -> JsonRpcRequest:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to JsonRpcRequest.")

        request_id = _read(data, "id")
        params = _read(data, "params")

        return cls(
            json_rpc=_as_string(_read(data, "jsonrpc")),
            id=None if request_id is _MISSING or request_id is None else _as_int32(request_id),
            method=_as_string(_read(data, "method")),
            params=None if params is _MISSING else params)


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


def _as_int32(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and -2**31 <= value < 2**31:
        return value

    raise ValueError("The JSON value could not be converted to System.Int32.")
