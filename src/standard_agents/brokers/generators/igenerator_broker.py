# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference


class IGeneratorBroker(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...

    @abstractmethod
    def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        ...

    # True when this broker puts resolved inference options on the wire. A broker that has not
    # opted in silently ignores them, and the answer is still held to shape, because the
    # Contract guardian validates and revises regardless (docs/per-request-inference.md 5).
    # Constrained decoding is an optimization over a guarantee the architecture already
    # provides; this flag exists so the trace can say which one happened.
    @property
    def honors_request(self) -> bool:
        return False

    # The request-carrying call: the same generation, with the run's resolved inference
    # options. Precedence has already been applied at the boundary, so a broker writes what it
    # is given and decides nothing. Default: degrade to the plain call, so the provider
    # packages keep working and opt in on their own schedule.
    async def generate_with_inference(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference) -> str:

        return await self.generate(system_prompt, user_prompt)

    # The streamed twin. A control a caller can step around by changing method is not a
    # control (SPEC.md 7.6): the streamed loop carries the same resolved options the batched
    # one does.
    def generate_stream_with_inference(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference) -> AsyncIterator[str]:

        return self.generate_stream(system_prompt, user_prompt)
