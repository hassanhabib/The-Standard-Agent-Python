# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Iterable

from standard_agents.brokers.classifiers.iclassifier_broker import IClassifierBroker

_ACCEPT = "accept"
_NO_CONFLICT = "NONE"


class RuleClassifierBroker(IClassifierBroker):
    def __init__(self, refuse_patterns: Iterable[str]) -> None:
        self._refuse_patterns = tuple(refuse_patterns)

    async def classify(self, input: str) -> str:
        matched_rule = next(
            (pattern for pattern in self._refuse_patterns
                if _contains_ordinal_ignore_case(input, pattern)),
            None)

        return (
            _ACCEPT if matched_rule is None
            else f"refuse: blocked by rule '{matched_rule}'")

    async def assess(self, system_prompt: str, input: str) -> str:
        return _NO_CONFLICT


# string.Contains(value, StringComparison.OrdinalIgnoreCase): each character compared by its
# simple (one character) upper-case mapping, never a culture's.
def _contains_ordinal_ignore_case(text: str, value: str) -> bool:
    return _to_upper_ordinal(value) in _to_upper_ordinal(text)


def _to_upper_ordinal(text: str) -> str:
    return "".join(
        upper if len(upper) == 1 else character
        for character, upper in ((character, character.upper()) for character in text))
