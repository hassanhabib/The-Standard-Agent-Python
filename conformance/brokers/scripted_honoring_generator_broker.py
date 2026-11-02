# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference

from conformance.brokers.scripted_generator_broker import ScriptedGeneratorBroker


class ScriptedHonoringGeneratorBroker(GeneratorBroker):
    """The scripted Brain that OPTS IN (docs/per-request-inference.md 5).

    It records every resolved inference it is handed, so a vector can certify what actually
    reached the wire: post-precedence, post-sanitization. Its sibling ScriptedGeneratorBroker
    deliberately does not opt in, which is how graceful degradation is certified against the
    interface's real default rather than a simulation of it.
    """

    def __init__(self, replies: Sequence[str], transient_failures: int = 0) -> None:
        self._inner = ScriptedGeneratorBroker(replies, transient_failures)
        self._inferences: list[ResolvedInference] = []

    @property
    def inferences(self) -> tuple[ResolvedInference, ...]:
        return tuple(self._inferences)

    @property
    def honors_request(self) -> bool:
        return True

    async def generate(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> str:
        if inference is not None:
            self._inferences.append(inference)

        return await self._inner.generate(system_prompt, user_prompt)

    async def generate_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> AsyncIterator[str]:
        if inference is not None:
            self._inferences.append(inference)

        async for token in self._inner.generate_stream(system_prompt, user_prompt):
            yield token
