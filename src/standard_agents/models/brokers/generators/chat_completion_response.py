# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from standard_agents.models.brokers.generators.chat_choice import ChatChoice

_MISSING = object()


# Wire names follow JsonNamingPolicy.SnakeCaseLower; reads are case-insensitive and nulls are
# written, as the broker's serializer options leave them.
@dataclass(frozen=True)
class ChatCompletionResponse:
    choices: tuple[ChatChoice, ...]

    def to_json_dict(self) -> dict:
        return {
            "choices": (
                None if self.choices is None
                else [
                    None if choice is None else choice.to_json_dict()
                    for choice in self.choices]),
        }

    @classmethod
    def from_json_dict(cls, data: dict) -> ChatCompletionResponse:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ChatCompletionResponse.")

        choices = _read(data, "choices")

        if choices is _MISSING or choices is None:
            return cls(choices=None)

        if not isinstance(choices, list):
            raise ValueError("The JSON value could not be converted to IReadOnlyList<ChatChoice>.")

        return cls(
            choices=tuple(
                None if choice is None else ChatChoice.from_json_dict(choice)
                for choice in choices))


# PropertyNameCaseInsensitive: every key matching ignoring case is read, the last one wins.
def _read(data: dict, name: str) -> Any:
    found = _MISSING

    for key, value in data.items():
        if key.lower() == name.lower():
            found = value

    return found
