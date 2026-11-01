# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


# What the Judge reviews with (SPEC.md 4.1): its rubric as the system prompt, the task, and the
# candidate answer, because an answer is good or bad for a question. The verdict is a score
# between 0.0 and 1.0 and a short reason.
class IVerifierBroker(ABC):
    @abstractmethod
    async def verify(self, system_prompt: str, task: str, candidate: str) -> str: ...
