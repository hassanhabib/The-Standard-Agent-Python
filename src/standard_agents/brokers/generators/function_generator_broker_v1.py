# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable, Sequence

from standard_agents.brokers.generators.igenerator_broker_v1 import IGeneratorBrokerV1
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ToolDefinition)


# The Custom mode for the V1 seam: a host-supplied conversation handler. Also what a test
# scripts, which is how native tool calling is certified without a provider.
class FunctionGeneratorBrokerV1(IGeneratorBrokerV1):
    def __init__(
        self,
        generate: Callable[
            [Sequence[ConversationMessage], Sequence[ToolDefinition]],
            Awaitable[GenerationResult]]) -> None:

        self._generate = generate

    async def generate(
        self,
        messages: Sequence[ConversationMessage],
        tools: Sequence[ToolDefinition]) -> GenerationResult:

        return await self._generate(messages, tools)
