# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Any

# Everything the core writes on the wire, on either protocol. The modeled field wins because
# the modeled field is the one precedence was applied to; a raw key that could beat it would be
# a second resolution path with no ceiling.
_CORE_OWNED_KEYS = frozenset({
    "model",
    "messages",
    "tools",
    "response_format",
    "temperature",
    "max_tokens",
    "seed",
    "stop",
    "stream",
})

# JsonDocumentOptions.MaxDepth's default, which JsonNode.Parse enforces.
_MAX_DEPTH = 64

# The characters JavaScriptEncoder.Default escapes even inside Basic Latin.
_HTML_SENSITIVE = frozenset('"&\'+<>`')

_SHORT_ESCAPES = {
    "\\": "\\\\",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
}


@dataclass(frozen=True)
class SanitizedProviderOptions:
    """What sanitizing a caller's provider options produced.

    The JSON that may reach the wire, the core-owned keys that were stripped from it, and
    whether the whole bag was unreadable.
    """

    json: str | None
    stripped_keys: tuple[str, ...]
    malformed: bool


class ProviderOptions:
    """The core-owned-keys rule (docs/per-request-inference.md 4.4).

    Every key the core writes on the wire is non-overridable. Enforced at the boundary by
    sanitize, so no broker, built-in or third-party, can ever be handed a passthrough that adds
    a tool, swaps the messages, or beats a value precedence already resolved, and again by
    merge_into, because this is the perimeter and one enforcement point is one forgotten call
    away from none.
    """

    @staticmethod
    def sanitize(provider_options_json: str | None) -> SanitizedProviderOptions:
        if _is_blank(provider_options_json):
            return SanitizedProviderOptions(json=None, stripped_keys=(), malformed=False)

        try:
            parsed = _parse_node(provider_options_json)
        except (ValueError, RecursionError):
            return SanitizedProviderOptions(json=None, stripped_keys=(), malformed=True)

        if not isinstance(parsed, dict):
            return SanitizedProviderOptions(json=None, stripped_keys=(), malformed=True)

        options = parsed
        stripped = tuple(key for key in options if key in _CORE_OWNED_KEYS)

        for key in stripped:
            del options[key]

        return SanitizedProviderOptions(
            json=_to_json_string(options) if options else None,
            stripped_keys=stripped,
            malformed=False)

    @staticmethod
    def merge_into(request: dict, sanitized_json: str | None) -> None:
        sanitized = ProviderOptions.sanitize(sanitized_json)

        if sanitized.json is None:
            return

        request.update(json.loads(sanitized.json))


class _RawNumber(str):
    """A number as it was written, the way a parsed JsonNode keeps the raw token."""


def _is_blank(text: str | None) -> bool:
    """Whether text is None or only whitespace, as string.IsNullOrWhiteSpace decides.

    Uses char.IsWhiteSpace's set, which str.isspace does not match: U+001C..U+001F are not
    whitespace to .NET.
    """
    if text is None:
        return True

    return all(
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp")
        for character in text)


def _reject_constant(constant: str) -> Any:
    raise ValueError(f"'{constant}' is an invalid JSON literal.")


def _parse_node(text: str) -> Any:
    """Parse as JsonNode.Parse does: strict JSON, no NaN or Infinity, nesting no deeper than 64."""
    node = json.loads(
        text,
        parse_int=_RawNumber,
        parse_float=_RawNumber,
        parse_constant=_reject_constant)

    _ensure_depth(node, depth=0)

    return node


def _ensure_depth(node: Any, depth: int) -> None:
    if isinstance(node, (dict, list)):
        depth += 1

        if depth > _MAX_DEPTH:
            raise ValueError(f"The maximum configured depth of {_MAX_DEPTH} has been exceeded.")

        children = node.values() if isinstance(node, dict) else node

        for child in children:
            _ensure_depth(child, depth)


def _to_json_string(node: Any) -> str:
    """Write as JsonNode.ToJsonString does with default options.

    Compact, and written with JavaScriptEncoder.Default.
    """
    if node is None:
        return "null"

    # Identity, not truthiness: a JSON boolean is told apart from the numbers 1 and 0.
    if node is True:
        return "true"

    if node is False:
        return "false"

    if isinstance(node, _RawNumber):
        return str(node)

    if isinstance(node, (int, float)):
        return json.dumps(node)

    if isinstance(node, str):
        return _escape(node)

    if isinstance(node, list):
        return "[" + ",".join(_to_json_string(item) for item in node) + "]"

    if isinstance(node, dict):
        return "{" + ",".join(
            _escape(key) + ":" + _to_json_string(value)
            for key, value in node.items()) + "}"

    raise TypeError(f"Cannot write {type(node).__name__} as JSON.")


def _escape(text: str) -> str:
    """Quote and escape a string as JavaScriptEncoder.Default does.

    Printable Basic Latin passes except the HTML-sensitive characters; everything else is
    escaped, as \\uXXXX in upper-case hex, surrogate pairs as two escapes.
    """
    parts = ['"']

    for character in text:
        code = ord(character)

        if character in _SHORT_ESCAPES:
            parts.append(_SHORT_ESCAPES[character])
        elif 0x20 <= code <= 0x7E and character not in _HTML_SENSITIVE:
            parts.append(character)
        elif code > 0xFFFF:
            code -= 0x10000
            parts.append(f"\\u{0xD800 + (code >> 10):04X}")
            parts.append(f"\\u{0xDC00 + (code & 0x3FF):04X}")
        else:
            parts.append(f"\\u{code:04X}")

    parts.append('"')

    return "".join(parts)
