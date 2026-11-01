# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Sequence

from standard_agents.brokers.generators.igenerator_broker_v1 import IGeneratorBrokerV1
from standard_agents.brokers.resiliences.iresilience_broker import IResilienceBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ToolDefinition)


# The same on the native path. A control that holds on one protocol and not the other is a
# control a caller can step around by changing configuration.
class RetryingGeneratorBrokerV1(IGeneratorBrokerV1):
    def __init__(
        self,
        generator_broker: IGeneratorBrokerV1,
        resilience_broker: IResilienceBroker) -> None:

        self._generator_broker = generator_broker
        self._resilience_broker = resilience_broker

    # Explicit pass-throughs, never the interface's defaults: a decorator that leaned on the
    # default member would silently drop the resolved options before the wire.
    @property
    def honors_request(self) -> bool:
        return self._generator_broker.honors_request

    async def generate(
        self,
        messages: Sequence[ConversationMessage],
        tools: Sequence[ToolDefinition]) -> GenerationResult:

        return await self._resilience_broker.execute(
            lambda: self._generator_broker.generate(messages, tools),
            GenerationResult)

    async def generate_with_inference(
        self,
        messages: Sequence[ConversationMessage],
        tools: Sequence[ToolDefinition],
        inference: ResolvedInference) -> GenerationResult:

        return await self._resilience_broker.execute(
            lambda: self._generator_broker.generate_with_inference(messages, tools, inference),
            GenerationResult)
