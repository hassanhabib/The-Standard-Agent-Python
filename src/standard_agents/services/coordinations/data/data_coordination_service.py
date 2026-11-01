# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.brokers.sessions.agent_session import AgentSession
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
        raise NotImplementedError

    async def remember(self, memory: str) -> None:
        raise NotImplementedError

    async def recall_session(self, session_id: str) -> AgentSession | None:
        raise NotImplementedError

    async def record_session(self, session: AgentSession) -> None:
        raise NotImplementedError

    async def retrieve_remote_tools(self) -> Sequence[McpTool]:
        raise NotImplementedError
