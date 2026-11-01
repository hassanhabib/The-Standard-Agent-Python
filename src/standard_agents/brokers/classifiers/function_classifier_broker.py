# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable

from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker


class FunctionClassifierBroker(ClassifierBroker):
    def __init__(
            self,
            screen: Callable[[str, str], Awaitable[str]],
            system_prompt: str) -> None:

        self._screen = screen
        self._system_prompt = system_prompt

    async def classify(self, input: str) -> str:
        return await self.assess(self._system_prompt, input)

    async def assess(self, system_prompt: str, input: str) -> str:
        return await self._screen(system_prompt, input)
