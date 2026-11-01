# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MISSING = object()


# Wire names follow JsonNamingPolicy.SnakeCaseLower; reads are case-insensitive and nulls are
# written, as the broker's serializer options leave them.
@dataclass(frozen=True)
class ChatDelta:
    content: str | None

    def to_json_dict(self) -> dict:
        return {
            "content": self.content,
        }

    @classmethod
    def from_json_dict(cls, data: dict) -> ChatDelta:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ChatDelta.")

        return cls(content=_as_string(_read(data, "content")))


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
