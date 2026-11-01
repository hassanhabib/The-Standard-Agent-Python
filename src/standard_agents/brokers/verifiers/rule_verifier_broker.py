# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Iterable

from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker

_PASS = "SCORE: 1.0\nREASON: ok"


class RuleVerifierBroker(VerifierBroker):
    def __init__(self, required_patterns: Iterable[str]) -> None:
        self._required_patterns = tuple(required_patterns)

    async def verify(self, task: str, candidate: str) -> str:
        missing_pattern = next(
            (pattern for pattern in self._required_patterns
                if not _contains_ordinal_ignore_case(candidate, pattern)),
            None)

        return (
            _PASS if missing_pattern is None
            else f"SCORE: 0.0\nREASON: missing required content '{missing_pattern}'")


def _contains_ordinal_ignore_case(text: str, value: str) -> bool:
    """Mirror .NET's string.Contains(value, StringComparison.OrdinalIgnoreCase)."""
    return _fold_ordinal_ignore_case(value) in _fold_ordinal_ignore_case(text)


def _fold_ordinal_ignore_case(text: str) -> str:
    """Uppercase each character by its simple (one character) mapping, never a culture's.

    A character whose Python uppercase expands to more than one character is kept as it is.
    """
    return "".join(
        upper if len(upper := character.upper()) == 1 else character
        for character in text)
