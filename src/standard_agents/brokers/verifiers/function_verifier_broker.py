# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import os
import unicodedata
from collections.abc import Awaitable, Callable

from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker


class FunctionVerifierBroker(VerifierBroker):
    def __init__(
            self,
            evaluate: Callable[[str, str], Awaitable[str]],
            system_prompt: str) -> None:

        self._evaluate = evaluate
        self._system_prompt = system_prompt

    async def verify(self, task: str, candidate: str) -> str:
        """Hand the host-supplied judge the task and the candidate together.

        The delegate's second argument stays a single piece of text while still carrying what
        SPEC.md 4.2 requires the Judge to see. The labels are the same ones the judge contract
        already uses.
        """
        return await self._evaluate(
            self._system_prompt,
            FunctionVerifierBroker.format_verdict_request(task, candidate))

    @staticmethod
    def format_verdict_request(task: str | None, candidate: str) -> str:
        """The candidate under the judge contract's labels, or alone when there is no task.

        Lines end with os.linesep, as .NET's Environment.NewLine.
        """
        return (
            candidate if _is_blank(task)
            else f"TASK: {task}{os.linesep}{os.linesep}ANSWER: {candidate}")


def _is_blank(text: str | None) -> bool:
    """Mirror .NET's string.IsNullOrWhiteSpace, with char.IsWhiteSpace's own set.

    That set is the Zs, Zl and Zp categories plus U+0009 to U+000D and U+0085; it differs from
    str.isspace, which also counts U+001C to U+001F.
    """
    if text is None:
        return True

    return all(
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp")
        for character in text)
