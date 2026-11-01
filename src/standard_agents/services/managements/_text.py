# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Text read the way the C# run reads it.

The run compares, trims and tests text with .NET's rules, and Python's own differ at the edges:
str.isspace counts U+001C..U+001F as white space and .NET does not.
"""

import unicodedata


def is_blank(text: str | None) -> bool:
    """string.IsNullOrWhiteSpace, over the .NET white-space set."""
    return text is None or all(_is_whitespace(character) for character in text)


def _is_whitespace(character: str) -> bool:
    """char.IsWhiteSpace, which string.Trim and string.IsNullOrWhiteSpace use."""
    return (
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp"))
