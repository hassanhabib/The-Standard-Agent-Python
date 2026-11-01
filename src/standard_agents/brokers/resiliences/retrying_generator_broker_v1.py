# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Sequence

from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.brokers.resiliences.resilience_broker import ResilienceBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ToolDefinition)


# The same on the native path. A control that holds on one protocol and not the other is a
# control a caller can step around by changing configuration.
class RetryingGeneratorBrokerV1(GeneratorBrokerV1):
    def __init__(
        self,
        generator_broker: GeneratorBrokerV1,
        resilience_broker: ResilienceBroker) -> None:

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
            tools: Sequence[ToolDefinition],
            *,
            inference: ResolvedInference | None = None) -> GenerationResult:

        return await self._resilience_broker.execute(
            lambda: self._generator_broker.generate(messages, tools, inference=inference),
            GenerationResult)
