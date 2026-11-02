# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MISSING = object()


@dataclass(frozen=True)
class ChatDelta:
    """The content a streamed chunk adds, None when it adds none.

    Wire names follow JsonNamingPolicy.SnakeCaseLower; reads are case-insensitive and nulls
    are written, as the broker's serializer options leave them.
    """

    content: str | None

    def to_json_dict(self) -> dict:
        return {
            "content": self.content,
        }

    @classmethod
    def from_json_dict(cls, data: dict) -> ChatDelta:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ChatDelta.")

        return cls(content=_as_string(_read_ignoring_case(data, "content")))


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
