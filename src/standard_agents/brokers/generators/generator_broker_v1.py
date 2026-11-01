# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ToolDefinition)


class GeneratorBrokerV1(ABC):
    """The V1 brain contract: a conversation in, a structured choice out.

    A sibling of GeneratorBroker, not a replacement (plan 1.3). V0 stays alive and supported,
    because the provider packages implement it and none of them should have to move on our
    schedule.
    """

    @abstractmethod
    async def generate(
            self,
            messages: Sequence[ConversationMessage],
            tools: Sequence[ToolDefinition],
            *,
            inference: ResolvedInference | None = None) -> GenerationResult:
        """A conversation in, a structured choice out.

        ``inference`` carries the run's resolved inference options, already
        precedence-resolved at the boundary. A broker that has not opted in ignores it, so
        provider packages keep working and opt in on their own schedule.
        """

    @property
    def honors_request(self) -> bool:
        """True when this broker puts resolved inference options on the wire.

        The guardian still holds the answer to shape either way (docs/per-request-inference.md 5).
        """
        return False
