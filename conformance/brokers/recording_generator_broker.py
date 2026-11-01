# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference


class RecordingGeneratorBroker(GeneratorBroker):
    """Wraps the scripted Brain and records everything it is shown.

    So a vector can certify what a model was and was not allowed to see. It wraps rather than
    replaces, so the real Brain path (redaction, rehydration, the streaming placeholder buffer)
    is what gets certified. Every member passes through explicitly, the same rule the core's own
    decorators follow: a wrapper that dropped the resolved inference or the opt-in would change
    what the scripted Brain was handed.
    """

    def __init__(self, inner: GeneratorBroker, record: Callable[[str], None]) -> None:
        self._inner = inner
        self._record = record

    @property
    def honors_request(self) -> bool:
        return self._inner.honors_request

    async def generate(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> str:
        self._record(system_prompt)
        self._record(user_prompt)

        return await self._inner.generate(system_prompt, user_prompt, inference=inference)

    async def generate_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> AsyncIterator[str]:
        self._record(system_prompt)
        self._record(user_prompt)

        tokens = self._inner.generate_stream(system_prompt, user_prompt, inference=inference)

        async for token in tokens:
            yield token
