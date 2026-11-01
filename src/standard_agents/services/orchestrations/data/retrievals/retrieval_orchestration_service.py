# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping, Sequence

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.services.foundations.external_tools.external_tool_service import (
    ExternalToolService)
from standard_agents.services.foundations.knowledges.knowledge_service import KnowledgeService
from standard_agents.services.foundations.skills.skill_service import SkillService


class RetrievalOrchestrationService:
    """Authored material, selected by relevance.

    Skills and knowledge share a region because they share a concept: both are written by
    someone, both are stored, and both are chosen for this prompt by how well they match it.
    """

    def __init__(
            self,
            *,
            skill_service: SkillService,
            knowledge_service: KnowledgeService,
            tool_catalog: str,
            logging_broker: LoggingBroker,
            external_tool_service: ExternalToolService,
            tool_catalog_entries: Mapping[str, str] | None = None) -> None:

        self.skill_service = skill_service
        self.knowledge_service = knowledge_service
        self.tool_catalog = tool_catalog
        self.logging_broker = logging_broker
        self.external_tool_service = external_tool_service
        self.tool_catalog_entries = tool_catalog_entries

    async def retrieve_instructions(self, route: str) -> str:
        raise NotImplementedError

    async def retrieve_grounding(self, query: str) -> Sequence[KnowledgeResult]:
        raise NotImplementedError

    async def retrieve_remote_tools(self) -> Sequence[McpTool]:
        raise NotImplementedError
