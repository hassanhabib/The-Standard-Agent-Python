# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The System.Text.Json behaviours the two MCP brokers rely on.

Python's json module does not have them: a parsed number that writes back the token it was read
from (JsonNode.ToJsonString), the default encoder's escaping (JsonSerializer.Serialize,
JsonNode.ToJsonString), and the exact text a member arrived as (JsonElement.GetRawText).
"""

from __future__ import annotations

import json
from typing import Any

_WHITESPACE = " \t\n\r"
_HTML_SENSITIVE = "&'+<>`"
_SHORT_ESCAPES = {"\\": "\\\\", "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r"}
_DECODER = json.JSONDecoder()


class JsonInteger(int):
    """A JSON integer that keeps its token: an int to every reader, its own text to the writer."""

    text: str

    def __new__(cls, text: str) -> JsonInteger:
        number = super().__new__(cls, int(text))
        number.text = text

        return number

    def __reduce__(self) -> tuple:
        return (JsonInteger, (self.text,))


class JsonFloat(float):
    """A JSON number with a fraction or an exponent, kept as JsonInteger keeps an integer."""

    text: str

    def __new__(cls, text: str) -> JsonFloat:
        number = super().__new__(cls, float(text))
        number.text = text

        return number

    def __reduce__(self) -> tuple:
        return (JsonFloat, (self.text,))


def parse(text: str) -> Any:
    """Parse as JsonNode.Parse does.

    Objects are dicts, arrays lists, numbers keep their tokens, and a JSON null is None. NaN and
    Infinity are not JSON to System.Text.Json, so they are not JSON here.
    """
    return json.loads(
        text,
        parse_int=JsonInteger,
        parse_float=JsonFloat,
        parse_constant=_reject_constant)


def to_json_string(value: Any) -> str:
    """Write as JsonNode.ToJsonString and JsonSerializer.Serialize with the default encoder do.

    No whitespace, numbers as they were read, and every character outside printable ASCII, every
    HTML-sensitive character and the double quote written as an uppercase \\uXXXX escape.
    """
    if value is None:
        return "null"

    # Identity, not truthiness: a bool is an int, and 1 and 0 must stay numbers.
    if value is True:
        return "true"

    if value is False:
        return "false"

    if isinstance(value, (JsonInteger, JsonFloat)):
        return value.text

    if isinstance(value, (int, float)):
        return repr(value)

    if isinstance(value, str):
        return _escape(value)

    if isinstance(value, dict):
        members = (f"{_escape(name)}:{to_json_string(member)}" for name, member in value.items())

        return "{" + ",".join(members) + "}"

    if isinstance(value, (list, tuple)):
        return "[" + ",".join(to_json_string(item) for item in value) + "]"

    if hasattr(value, "to_json_dict"):
        return to_json_string(value.to_json_dict())

    raise TypeError(f"The type '{type(value).__name__}' cannot be written as JSON.")


def raw_member(text: str | None, name: str) -> str | None:
    """JsonElement.GetRawText of an object's member.

    Matched as the case-insensitive deserializer matches it (the last member whose name matches
    ignoring case). None when text is not an object or has no such member. text must already be
    valid JSON.
    """
    if text is None:
        return None

    index = _skip_whitespace(text, 0)

    if index >= len(text) or text[index] != "{":
        return None

    found: str | None = None
    index = _skip_whitespace(text, index + 1)

    if text[index] == "}":
        return None

    while True:
        member_name, index = json.decoder.scanstring(text, index + 1)
        index = _skip_whitespace(text, index)
        start = _skip_whitespace(text, index + 1)
        _, end = _DECODER.raw_decode(text, start)

        if member_name.lower() == name.lower():
            found = text[start:end]

        index = _skip_whitespace(text, end)

        if text[index] == "}":
            return found

        index = _skip_whitespace(text, index + 1)


def raw_items(text: str | None) -> list[str] | None:
    """JsonElement.GetRawText of each item of an array. None when text is not an array."""
    if text is None:
        return None

    index = _skip_whitespace(text, 0)

    if index >= len(text) or text[index] != "[":
        return None

    items: list[str] = []
    index = _skip_whitespace(text, index + 1)

    if text[index] == "]":
        return items

    while True:
        _, end = _DECODER.raw_decode(text, index)
        items.append(text[index:end])
        index = _skip_whitespace(text, end)

        if text[index] == "]":
            return items

        index = _skip_whitespace(text, index + 1)


def _escape(value: str) -> str:
    escaped: list[str] = ['"']

    for character in value:
        if character in _SHORT_ESCAPES:
            escaped.append(_SHORT_ESCAPES[character])

        elif character == '"' or character in _HTML_SENSITIVE:
            escaped.append(f"\\u{ord(character):04X}")

        elif " " <= character <= "~":
            escaped.append(character)

        elif ord(character) > 0xFFFF:
            code_point = ord(character) - 0x10000
            escaped.append(f"\\u{0xD800 + (code_point >> 10):04X}")
            escaped.append(f"\\u{0xDC00 + (code_point & 0x3FF):04X}")

        else:
            escaped.append(f"\\u{ord(character):04X}")

    escaped.append('"')

    return "".join(escaped)


def _skip_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index] in _WHITESPACE:
        index += 1

    return index


def _reject_constant(constant: str) -> Any:
    raise json.JSONDecodeError(f"'{constant}' is an invalid JSON literal.", constant, 0)
