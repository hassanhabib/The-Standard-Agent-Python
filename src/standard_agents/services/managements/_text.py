# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Text read the way the C# run reads it.

The run compares, trims and tests text with .NET's rules, and Python's own differ at the edges:
str.isspace counts U+001C..U+001F as white space and .NET does not, and str.upper applies full
case mappings where OrdinalIgnoreCase compares by simple ones.
"""

import re
import unicodedata

# What string.ReplaceLineEndings recognizes as a line ending: CRLF, CR, LF, FF, NEL, LS and PS.
_LINE_ENDINGS = re.compile(r"\r\n|[\r\n\f\x85  ]")


def is_blank(text: str | None) -> bool:
    """string.IsNullOrWhiteSpace, over the .NET white-space set."""
    return text is None or all(_is_whitespace(character) for character in text)


def trim_start(text: str) -> str:
    """string.TrimStart, over the .NET white-space set."""
    start = 0

    while start < len(text) and _is_whitespace(text[start]):
        start += 1

    return text[start:]


def trim_end(text: str) -> str:
    """string.TrimEnd, over the .NET white-space set."""
    end = len(text)

    while end > 0 and _is_whitespace(text[end - 1]):
        end -= 1

    return text[:end]


def trim(text: str) -> str:
    """string.Trim, over the .NET white-space set."""
    return trim_end(trim_start(text))


def replace_line_endings(text: str, replacement: str) -> str:
    """string.ReplaceLineEndings(replacement)."""
    return _LINE_ENDINGS.sub(replacement, text)


def fold(value: str) -> str:
    """Fold a string the way StringComparison.OrdinalIgnoreCase compares it.

    Characters compare by their simple uppercase mapping, so each character is uppercased on
    its own and kept as it is when its mapping expands (U+00DF would otherwise become "SS").
    Folding keeps the length, so a folded substring is a substring of the folded text.
    """
    folded: list[str] = []

    for character in value:
        candidate = character.upper()
        folded.append(candidate if len(candidate) == 1 else character)

    return "".join(folded)


def contains_ignoring_case(text: str, value: str) -> bool:
    """string.Contains(value, StringComparison.OrdinalIgnoreCase)."""
    return fold(value) in fold(text)


def starts_with_ignoring_case(text: str, prefix: str) -> bool:
    """string.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)."""
    return fold(text[:len(prefix)]) == fold(prefix)


def _is_whitespace(character: str) -> bool:
    """char.IsWhiteSpace, which string.Trim and string.IsNullOrWhiteSpace use."""
    return (
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp"))
