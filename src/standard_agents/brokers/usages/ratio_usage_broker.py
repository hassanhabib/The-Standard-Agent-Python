# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import math
import unicodedata

from standard_agents.brokers.usages.usage_broker import UsageBroker


class RatioUsageBroker(UsageBroker):
    """The Local mode: a tokenizer in the box.

    A budget works against any endpoint without asking the host to install anything.

    It is an ESTIMATE and says so: every number it produces is marked is_estimated, because a
    budget you can enforce and a number you can bill against are not the same claim. Word-aware
    rather than a flat characters/4: whitespace is not billed, and a long word costs more than a
    short one, which is where a flat ratio drifts worst on code and identifiers.

    A host that needs exactness supplies the provider's own tokenizer through use_usage.
    """

    def __init__(self, characters_per_token: float = 4.0) -> None:
        """Counts against characters_per_token, four by default.

        Four is roughly the average characters-per-token for English BPE vocabularies. It is a
        ratio and not a rule, which is the whole reason the result is flagged as estimated, and
        why it is settable, since code and denser-tokenizing languages sit well below it.
        """
        # Written as a negation so NaN is refused too.
        if not characters_per_token > 0:
            raise ValueError(
                "Characters per token must be greater than zero. "
                "(Parameter 'charactersPerToken')")

        self._characters_per_token = characters_per_token

    async def count_tokens(self, text: str) -> int:
        if _is_blank(text):
            return 0

        # Every word costs at least one token however short it is, and a longer one splits into
        # subwords rather than scaling smoothly with its length.
        return sum(
            max(1, math.ceil(_utf16_length(word) / self._characters_per_token))
            for word in _split_on_white_space(text))


def _utf16_length(text: str) -> int:
    """The length .NET's string.Length reports: UTF-16 code units.

    A character outside the Basic Multilingual Plane counts as two.
    """
    return len(text.encode("utf-16-le", errors="surrogatepass")) // 2


def _is_white_space(character: str) -> bool:
    """.NET's char.IsWhiteSpace: Zs, Zl and Zp plus U+0009 to U+000D and U+0085.

    Differs from str.isspace, which also counts U+001C to U+001F.
    """
    if character in "\t\n\v\f\r\x85":
        return True

    return unicodedata.category(character) in ("Zs", "Zl", "Zp")


def _is_blank(text: str | None) -> bool:
    """True for None, empty, or all whitespace, as .NET's string.IsNullOrWhiteSpace decides."""
    if text is None:
        return True

    return all(_is_white_space(character) for character in text)


def _split_on_white_space(value: str) -> list[str]:
    """The words between runs of .NET whitespace, with no empty entries.

    Mirrors string.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries).
    """
    parts: list[str] = []
    current: list[str] = []

    for character in value:
        if _is_white_space(character):
            if current:
                parts.append("".join(current))
                current = []
        else:
            current.append(character)

    if current:
        parts.append("".join(current))

    return parts
