# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import os
import unicodedata
from typing import Awaitable, Callable

from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker


class FunctionVerifierBroker(IVerifierBroker):
    def __init__(
        self,
        evaluate: Callable[[str, str], Awaitable[str]],
        system_prompt: str) -> None:

        self._evaluate = evaluate
        self._system_prompt = system_prompt

    # A host-supplied judge is handed the task and the candidate together, so the delegate's
    # second argument stays a single piece of text while still carrying what SPEC.md 4.2
    # requires the Judge to see. The labels are the same ones the judge contract already uses.
    async def verify(self, task: str, candidate: str) -> str:
        return await self._evaluate(
            self._system_prompt,
            FunctionVerifierBroker.format_verdict_request(task, candidate))

    # Environment.NewLine is os.linesep.
    @staticmethod
    def format_verdict_request(task: str | None, candidate: str) -> str:
        return (
            candidate if _is_null_or_white_space(task)
            else f"TASK: {task}{os.linesep}{os.linesep}ANSWER: {candidate}")


# string.IsNullOrWhiteSpace, with char.IsWhiteSpace's own set.
def _is_null_or_white_space(text: str | None) -> bool:
    if text is None:
        return True

    return all(
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp")
        for character in text)
