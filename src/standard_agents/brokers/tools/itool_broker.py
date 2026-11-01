# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod


class IToolBroker(ABC):
    @abstractmethod
    async def has(self, name: str) -> bool:
        ...

    @abstractmethod
    async def run(self, name: str, input: str) -> str:
        ...

    @abstractmethod
    async def compensate(self, name: str, input: str, outcome: str) -> str:
        ...
