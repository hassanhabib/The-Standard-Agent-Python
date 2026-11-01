# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import AsyncIterator

from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.brokers.resiliences.iresilience_broker import IResilienceBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference


# Retry by decoration, not by a service holding a second broker.
#
# Resilience does not get logging's utility exemption. Logging is write-only observability and
# cannot change what the agent does; resilience decides whether the call happens again, which
# is control flow. A foundation holding a thing that re-runs its own broker is not "one broker,
# one resource", so the wrapping happens at composition and BrainService never learns retry
# exists.
#
# A retried call is still one turn (SPEC.md 4.10): retries happen inside the call, so the loop's
# turn budget counts the agent's reasoning rather than the network's luck.
class RetryingGeneratorBroker(IGeneratorBroker):
    def __init__(
        self,
        generator_broker: IGeneratorBroker,
        resilience_broker: IResilienceBroker) -> None:

        self._generator_broker = generator_broker
        self._resilience_broker = resilience_broker

    # A decorator that leaned on the interface's default member would silently drop the
    # resolved options before the wire: the default degrades on the DECORATOR, not on the broker
    # it wraps. Every pass-through here is explicit for that reason, and so is the flag.
    @property
    def honors_request(self) -> bool:
        return self._generator_broker.honors_request

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return await self._resilience_broker.execute(
            lambda: self._generator_broker.generate(system_prompt, user_prompt),
            str)

    async def generate_with_inference(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference) -> str:

        return await self._resilience_broker.execute(
            lambda: self._generator_broker.generate_with_inference(
                system_prompt, user_prompt, inference),
            str)

    # Streaming passes straight through, exactly as it did before. A stream that has already
    # yielded tokens cannot be retried from the start without the caller seeing them twice, and
    # silently replaying a partial answer is worse than surfacing the failure.
    def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        return self._generator_broker.generate_stream(system_prompt, user_prompt)

    def generate_stream_with_inference(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference) -> AsyncIterator[str]:

        return self._generator_broker.generate_stream_with_inference(
            system_prompt, user_prompt, inference)
