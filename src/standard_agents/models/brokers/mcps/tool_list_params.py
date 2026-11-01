# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MISSING = object()


@dataclass(frozen=True)
class ToolListParams:
    """The params of a tools/list request: the cursor of the page to read.

    Wire names follow JsonNamingPolicy.CamelCase; reads are case-insensitive and null values are
    omitted on write (WhenWritingNull), as the HttpMcpBroker's serializer options leave them.
    """

    cursor: str

    def to_json_dict(self) -> dict:
        values = {
            "cursor": self.cursor,
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> ToolListParams:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ToolListParams.")

        return cls(cursor=_as_string(_read_ignoring_case(data, "cursor")))


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
