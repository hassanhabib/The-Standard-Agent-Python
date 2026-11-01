# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from standard_agents.models.brokers.classifiers.chat_message import ChatMessage

_MISSING = object()


# Wire names follow JsonNamingPolicy.SnakeCaseLower; reads are case-insensitive and nulls are
# written, as the broker's serializer options leave them.
@dataclass(frozen=True)
class ChatChoice:
    message: ChatMessage

    def to_json_dict(self) -> dict:
        return {
            "message": None if self.message is None else self.message.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, data: dict) -> ChatChoice:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ChatChoice.")

        message = _read(data, "message")

        return cls(
            message=(
                None if message is _MISSING or message is None
                else ChatMessage.from_json_dict(message)))


# PropertyNameCaseInsensitive: every key matching ignoring case is read, the last one wins.
def _read(data: dict, name: str) -> Any:
    found = _MISSING

    for key, value in data.items():
        if key.lower() == name.lower():
            found = value

    return found
