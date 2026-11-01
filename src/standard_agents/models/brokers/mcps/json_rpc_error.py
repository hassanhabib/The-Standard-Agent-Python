# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MISSING = object()


@dataclass(frozen=True)
class JsonRpcError:
    """The error a JSON-RPC response carries.

    Wire names follow JsonNamingPolicy.CamelCase; reads are case-insensitive and null values are
    omitted on write (WhenWritingNull), as the HttpMcpBroker's serializer options leave them.
    """

    code: int
    message: str

    def to_json_dict(self) -> dict:
        values = {
            "code": self.code,
            "message": self.message,
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> JsonRpcError:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to JsonRpcError.")

        code = _read_ignoring_case(data, "code")

        return cls(
            code=0 if code is _MISSING else _as_int32(code),
            message=_as_string(_read_ignoring_case(data, "message")))


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
