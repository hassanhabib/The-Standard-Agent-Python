# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ToolDefinition)


# The V1 brain contract: a conversation in, a structured choice out.
#
# A sibling of IGeneratorBroker, not a replacement (plan 1.3). V0 stays alive and supported,
# because the provider packages implement it and none of them should have to move on our
# schedule.
class IGeneratorBrokerV1(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: Sequence[ConversationMessage],
        tools: Sequence[ToolDefinition]) -> GenerationResult:
        ...

    # True when this broker puts resolved inference options on the wire
    # (docs/per-request-inference.md 5); the guardian still holds the answer to shape either way.
    @property
    def honors_request(self) -> bool:
        return False

    # The request-carrying call: the same generation with the run's resolved inference options,
    # already precedence-resolved at the boundary. Default: degrade to the plain call, so
    # provider packages keep working and opt in on their own schedule.
    async def generate_with_inference(
        self,
        messages: Sequence[ConversationMessage],
        tools: Sequence[ToolDefinition],
        inference: ResolvedInference) -> GenerationResult:

        return await self.generate(messages, tools)
