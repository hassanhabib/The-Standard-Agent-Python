# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


# What the Gate screens with (SPEC.md 4.1): its rubric as the system prompt, the input to screen,
# and a verdict back: accept, route: <label>, or refuse: <reason>.
class IClassifierBroker(ABC):
    @abstractmethod
    async def classify(self, system_prompt: str, input: str) -> str: ...
