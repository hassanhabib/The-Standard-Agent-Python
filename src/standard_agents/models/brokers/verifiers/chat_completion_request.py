# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from standard_agents.models.brokers.verifiers.chat_message import ChatMessage

_MISSING = object()


@dataclass(frozen=True)
class ChatCompletionRequest:
    """A chat completion request as the broker sends it.

    Wire names follow JsonNamingPolicy.SnakeCaseLower; reads are case-insensitive and nulls
    are written, as the broker's serializer options leave them.
    """

    model: str
    messages: tuple[ChatMessage, ...]
    stream: bool
    temperature: float
    max_tokens: int

    def to_json_dict(self) -> dict:
        return {
            "model": self.model,
            "messages": (
                None if self.messages is None
                else [
                    None if message is None else message.to_json_dict()
                    for message in self.messages]),
            "stream": self.stream,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    @classmethod
    def from_json_dict(cls, data: dict) -> ChatCompletionRequest:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ChatCompletionRequest.")

        model = _read_ignoring_case(data, "model")
        messages = _read_ignoring_case(data, "messages")
        stream = _read_ignoring_case(data, "stream")
        temperature = _read_ignoring_case(data, "temperature")
        max_tokens = _read_ignoring_case(data, "max_tokens")

        if messages is _MISSING or messages is None:
            parsed_messages = None
        elif isinstance(messages, list):
            parsed_messages = tuple(
                None if message is None else ChatMessage.from_json_dict(message)
                for message in messages)
        else:
            raise ValueError(
                "The JSON value could not be converted to IReadOnlyList<ChatMessage>.")

        return cls(
            model=_as_string(model),
            messages=parsed_messages,
            stream=False if stream is _MISSING else _as_bool(stream),
            temperature=0.0 if temperature is _MISSING else _as_double(temperature),
            max_tokens=0 if max_tokens is _MISSING else _as_int32(max_tokens))


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


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    raise ValueError("The JSON value could not be converted to System.Boolean.")


def _as_double(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    raise ValueError("The JSON value could not be converted to System.Double.")


def _as_int32(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and -2**31 <= value < 2**31:
        return value

    raise ValueError("The JSON value could not be converted to System.Int32.")
