# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from standard_agents.models.brokers.generators.chat_delta import ChatDelta

_MISSING = object()


# Wire names follow JsonNamingPolicy.SnakeCaseLower; reads are case-insensitive and nulls are
# written, as the broker's serializer options leave them.
@dataclass(frozen=True)
class ChatChoiceDelta:
    delta: ChatDelta

    def to_json_dict(self) -> dict:
        return {
            "delta": None if self.delta is None else self.delta.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, data: dict) -> ChatChoiceDelta:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ChatChoiceDelta.")

        delta = _read(data, "delta")

        return cls(
            delta=(
                None if delta is _MISSING or delta is None
                else ChatDelta.from_json_dict(delta)))


# PropertyNameCaseInsensitive: every key matching ignoring case is read, the last one wins.
def _read(data: dict, name: str) -> Any:
    found = _MISSING

    for key, value in data.items():
        if key.lower() == name.lower():
            found = value

    return found
