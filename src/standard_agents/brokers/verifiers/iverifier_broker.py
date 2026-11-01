# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


# What the Judge reviews with: the task travels with the candidate, because an answer is good
# or bad for a question. The verdict is "<score between 0 and 1> <optional reason>".
class IVerifierBroker(ABC):
    @abstractmethod
    async def verify(self, task: str, candidate: str) -> str: ...
