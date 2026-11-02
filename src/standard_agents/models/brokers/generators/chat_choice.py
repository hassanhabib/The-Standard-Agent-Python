# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from standard_agents.models.brokers.generators.chat_message import ChatMessage

_MISSING = object()


@dataclass(frozen=True)
class ChatChoice:
    """One choice of a chat completion: the message the model returned.

    Wire names follow JsonNamingPolicy.SnakeCaseLower; reads are case-insensitive and nulls
    are written, as the broker's serializer options leave them.
    """

    message: ChatMessage

    def to_json_dict(self) -> dict:
        return {
            "message": None if self.message is None else self.message.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, data: dict) -> ChatChoice:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ChatChoice.")

        message = _read_ignoring_case(data, "message")

        return cls(
            message=(
                None if message is _MISSING or message is None
                else ChatMessage.from_json_dict(message)))


def _read_ignoring_case(data: dict, name: str) -> Any:
    """Read a property the way PropertyNameCaseInsensitive does.

    Every key that matches the name ignoring case is read, and the last one wins.
    """
    found = _MISSING

    for key, value in data.items():
        if key.lower() == name.lower():
            found = value

    return found
