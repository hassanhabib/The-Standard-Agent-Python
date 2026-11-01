# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ToolDefinition)


class FunctionGeneratorBrokerV1(GeneratorBrokerV1):
    """The Custom mode for the V1 seam: a host-supplied conversation handler.

    Also what a test scripts, which is how native tool calling is certified without a provider.
    """

    def __init__(
            self,
            generate: Callable[
                [Sequence[ConversationMessage], Sequence[ToolDefinition]],
                Awaitable[GenerationResult]]) -> None:

        self._generate = generate

    async def generate(
            self,
            messages: Sequence[ConversationMessage],
            tools: Sequence[ToolDefinition],
            *,
            inference: ResolvedInference | None = None) -> GenerationResult:

        return await self._generate(messages, tools)
