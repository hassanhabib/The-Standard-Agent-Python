# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Iterable

from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker

_ACCEPT = "accept"
_NO_CONFLICT = "NONE"


class RuleClassifierBroker(ClassifierBroker):
    def __init__(self, refuse_patterns: Iterable[str]) -> None:
        self._refuse_patterns = tuple(refuse_patterns)

    async def classify(self, input: str) -> str:
        matched_rule = next(
            (pattern for pattern in self._refuse_patterns
             if _contains_ordinal_ignore_case(input, pattern)),
            None)

        if matched_rule is None:
            return _ACCEPT

        return f"refuse: blocked by rule '{matched_rule}'"

    async def assess(self, system_prompt: str, input: str) -> str:
        return _NO_CONFLICT


def _contains_ordinal_ignore_case(text: str, value: str) -> bool:
    """string.Contains(value, StringComparison.OrdinalIgnoreCase).

    Each character is compared by its simple (one character) upper-case mapping, never a
    culture's.
    """
    return _to_upper_ordinal(value) in _to_upper_ordinal(text)


def _to_upper_ordinal(text: str) -> str:
    """Uppercases each character on its own, keeping it as it is when its mapping expands."""
    folded: list[str] = []

    for character in text:
        upper = character.upper()
        folded.append(upper if len(upper) == 1 else character)

    return "".join(folded)
