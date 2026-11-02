# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod


class ClassifierBroker(ABC):
    @abstractmethod
    async def classify(self, input: str) -> str:
        ...

    @abstractmethod
    async def assess(self, system_prompt: str, input: str) -> str:
        ...
