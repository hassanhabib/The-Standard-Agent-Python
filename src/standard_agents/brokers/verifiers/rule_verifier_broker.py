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
                if _contains_ordinal_ignore_case(candidate, pattern) is False),
            None)

        return (
            _PASS if missing_pattern is None
            else f"SCORE: 0.0\nREASON: missing required content '{missing_pattern}'")


# string.Contains(value, StringComparison.OrdinalIgnoreCase): each character compared by its
# simple (one character) upper-case mapping, never a culture's.
def _contains_ordinal_ignore_case(text: str, value: str) -> bool:
    return _to_upper_ordinal(value) in _to_upper_ordinal(text)


def _to_upper_ordinal(text: str) -> str:
    return "".join(
        upper if len(upper) == 1 else character
        for character, upper in ((character, character.upper()) for character in text))
