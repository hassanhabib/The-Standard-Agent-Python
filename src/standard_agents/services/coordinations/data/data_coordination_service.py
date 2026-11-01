# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.brokers.sessions.agent_session import AgentSession
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.orchestrations.data.recollections \
    .recollection_orchestration_service import RecollectionOrchestrationService
from standard_agents.services.orchestrations.data.retrievals \
    .retrieval_orchestration_service import RetrievalOrchestrationService


class DataCoordinationService:
    """The Data nature: two regions, and the composing that belongs to neither of them.

    Retrieval brings authored material selected by relevance; Recollection brings what the
    agent accumulated. Deciding that both land in one system prompt and one observation list is
    this tier's job, because it is the only place that can see both.
    """

    def __init__(
            self,
            *,
            retrieval_service: RetrievalOrchestrationService,
            recollection_service: RecollectionOrchestrationService,
            logging_broker: LoggingBroker) -> None:

        self.retrieval_service = retrieval_service
        self.recollection_service = recollection_service
        self.logging_broker = logging_broker

    async def recall(self, context: AgentContext) -> AgentContext:
        system_prompt = await self.retrieval_service.retrieve_instructions(context.route)
        memories = await self.recollection_service.recall_memories()
        knowledge = await self.retrieval_service.retrieve_grounding(context.prompt)
        passages = (knowledge_result.text for knowledge_result in knowledge)

        return dataclasses.replace(
            context,
            system_prompt=system_prompt,
            observations=(*context.observations, *memories, *passages),
            grounding_sources=_with_grounding_sources(context.grounding_sources, knowledge))

    async def remember(self, memory: str) -> None:
        await self.recollection_service.remember(memory)

    async def recall_session(self, session_id: str) -> AgentSession | None:
        raise NotImplementedError

    async def record_session(self, session: AgentSession) -> None:
        raise NotImplementedError

    async def retrieve_remote_tools(self) -> Sequence[McpTool]:
        raise NotImplementedError


def _with_grounding_sources(
        grounding_sources: tuple[str, ...],
        knowledge: Sequence[KnowledgeResult]) -> tuple[str, ...]:
    """Each source once, in the order first recalled, and never an empty one.

    A passage whose origin is unknown can never be cited (SPEC.md 3.2, 3.7). Recall runs every
    turn, so what an earlier turn recalled is already here and keeps its place.
    """
    recalled_sources = (
        knowledge_result.source for knowledge_result in knowledge
        if knowledge_result.source and not knowledge_result.source.isspace())

    return tuple(dict.fromkeys((*grounding_sources, *recalled_sources)))
