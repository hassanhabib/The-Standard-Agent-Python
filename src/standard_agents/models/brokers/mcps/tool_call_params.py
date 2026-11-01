# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MISSING = object()


# Arguments are whatever JSON object the caller shaped (a native call's own arguments, or plain
# text wrapped upstream), carried as parsed JSON so the broker never interprets them.
#
# Wire names follow JsonNamingPolicy.CamelCase; reads are case-insensitive and null values are
# omitted on write (WhenWritingNull), as the McpBroker's serializer options leave them.
@dataclass(frozen=True)
class ToolCallParams:
    name: str
    arguments: Any | None

    def to_json_dict(self) -> dict:
        values = {
            "name": self.name,
            "arguments": self.arguments,
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> ToolCallParams:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ToolCallParams.")

        arguments = _read(data, "arguments")

        return cls(
            name=_as_string(_read(data, "name")),
            arguments=None if arguments is _MISSING else arguments)


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
