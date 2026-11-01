# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod


class VerifierBroker(ABC):
    @abstractmethod
    async def verify(self, task: str, candidate: str) -> str:
        """Return a verdict on the candidate as an answer to the task.

        The task travels with the candidate: an answer is good or bad FOR a question, and a
        verdict on a fit the verifier cannot see is noise dressed as a number (SPEC.md 4.2).
        """
