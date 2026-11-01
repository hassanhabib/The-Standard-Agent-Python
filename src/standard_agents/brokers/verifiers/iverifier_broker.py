# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod


class IVerifierBroker(ABC):
    # The task travels with the candidate: an answer is good or bad FOR a question, and a
    # verdict on a fit the verifier cannot see is noise dressed as a number (SPEC.md 4.2).
    @abstractmethod
    async def verify(self, task: str, candidate: str) -> str:
        ...
