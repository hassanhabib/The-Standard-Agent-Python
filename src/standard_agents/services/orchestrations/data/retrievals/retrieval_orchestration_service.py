# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping, Sequence

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyException,
    ExternalToolDependencyValidationException,
    ExternalToolServiceException)
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.services.foundations.external_tools.external_tool_service import (
    ExternalToolService)
from standard_agents.services.foundations.knowledges.knowledge_service import KnowledgeService
from standard_agents.services.foundations.skills.skill_service import SkillService

_TOOLS_MARKER = "{{tools}}"


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
        skills = await self.skill_service.retrieve_skills(route)

        return skills.replace(_TOOLS_MARKER, await self._render_tool_catalog(skills))

    async def retrieve_grounding(self, query: str) -> Sequence[KnowledgeResult]:
        raise NotImplementedError

    async def retrieve_remote_tools(self) -> Sequence[McpTool]:
        """Every tool the servers declared, described or not.

        The callers apply the opt-in themselves: selection judges described names, the native
        list advertises described definitions, and the perimeter binds described names.
        """
        return await self.external_tool_service.retrieve_tools()

    async def _render_tool_catalog(self, skills: str) -> str:
        """Remote tools join the catalog only when the marker is present.

        An agent that never advertises never pays a discovery call.
        """
        if _TOOLS_MARKER not in skills:
            return self.tool_catalog

        remote_catalog = _render_remote_tool_catalog(await self._discover_remote_tools())

        if not remote_catalog:
            return self.tool_catalog

        return f"{self.tool_catalog}\n{remote_catalog}"

    async def _discover_remote_tools(self) -> Sequence[McpTool]:
        """Best effort: a server down at discovery hides only its own tools this turn.

        The foundation has already localized and logged its failure at the severity it earned,
        so this tier degrades to no remote tools rather than failing the run.
        """
        try:
            return await self.external_tool_service.retrieve_tools()
        except ExternalToolDependencyException:
            return ()
        except ExternalToolDependencyValidationException:
            return ()
        except ExternalToolServiceException:
            return ()


def _render_remote_tool_catalog(remote_tools: Sequence[McpTool]) -> str:
    catalog_lines = (
        f"- {tool.name} \u2014 {tool.description} parameters: {tool.input_schema_json}"
        for tool in remote_tools
        if tool.description and not tool.description.isspace())

    return "\n".join(catalog_lines)
