# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyException,
    ExternalToolDependencyValidationException,
    ExternalToolServiceException)
from standard_agents.models.foundations.knowledges.exceptions import (
    KnowledgeDependencyException,
    KnowledgeServiceException,
    KnowledgeValidationException)
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.models.foundations.memories.exceptions import (
    MemoryDependencyException,
    MemoryServiceException,
    MemoryValidationException)
from standard_agents.models.foundations.sessions.exceptions import (
    SessionDependencyException,
    SessionServiceException,
    SessionValidationException)
from standard_agents.models.foundations.skills.exceptions import (
    SkillDependencyException,
    SkillServiceException)
from standard_agents.models.loggings.agent_run import AgentRun
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    FailedAgentOrchestrationServiceException)
from standard_agents.services.foundations.external_tools.external_tool_service import (
    ExternalToolService)
from standard_agents.services.foundations.knowledges.knowledge_service import KnowledgeService
from standard_agents.services.foundations.skills.skill_service import SkillService
from xeptions import Xeption

_TOOLS_MARKER = "{{tools}}"
_SKILLS_MARKER = "{{skills}}"


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
        """Compose the region.

        tool_catalog_entries is the catalog per tool (name to its rendered line), so a run
        under selection (SPEC.md 4.15) can be shown only what it was offered. None keeps the
        whole-string catalog the only source.
        """
        self.skill_service = skill_service
        self.knowledge_service = knowledge_service
        self.tool_catalog = tool_catalog
        self.logging_broker = logging_broker
        self.external_tool_service = external_tool_service
        self.tool_catalog_entries = tool_catalog_entries

        # Kept after the first successful discovery, so a healthy server is asked once per
        # composition rather than once per prompt.
        self._remote_tools: Sequence[McpTool] | None = None

    async def retrieve_instructions(self, route: str) -> str:
        """The applicable skills, with the tool and skill catalog markers expanded.

        The catalogs are expanded here rather than in a skill file, because which tools a
        Brain may reach for is a safety boundary and the marker is the developer's opt-in
        (SPEC.md 6.1).
        """
        async with _handling_exceptions(self.logging_broker):
            skills = await self.skill_service.retrieve_skills(route)

            instructions = skills.replace(
                _TOOLS_MARKER, await self._render_tool_catalog(skills))

            if _SKILLS_MARKER in instructions:
                skill_catalog = await self.skill_service.retrieve_skill_catalog()
                instructions = instructions.replace(_SKILLS_MARKER, skill_catalog)

            return instructions

    async def retrieve_grounding(self, query: str) -> Sequence[KnowledgeResult]:
        """The passages that answer this prompt, best first, each with its source (SPEC.md 3.7).

        Empty when the knowledge broker cannot say.
        """
        async with _handling_exceptions(self.logging_broker):
            knowledge = await self.knowledge_service.retrieve_sourced_knowledge(query)

            await self.logging_broker.log_process(
                "Data", f"Retrieved {len(knowledge)} knowledge matches")

            return knowledge

    async def retrieve_remote_tools(self) -> Sequence[McpTool]:
        """Every tool the servers declared, described or not.

        The callers apply the opt-in themselves: selection judges described names, the native
        list advertises described definitions, and the perimeter binds described names.
        """
        async with _handling_exceptions(self.logging_broker):
            return await self._discover_remote_tools()

    def _selected_tool_catalog(self) -> str:
        """The local catalog a run under selection (SPEC.md 4.15) is shown.

        Read off the ambient run, so no renderer gains a parameter for it. Absent a selection,
        or absent the per-tool entries, the whole catalog renders unchanged.
        """
        offered_tools = _offered_tools()

        if offered_tools is None or self.tool_catalog_entries is None:
            return self.tool_catalog

        return "\n".join(
            catalog_line for tool_name, catalog_line in self.tool_catalog_entries.items()
            if _is_offered(tool_name, offered_tools))

    async def _render_tool_catalog(self, skills: str) -> str:
        """Remote tools join the catalog only when the marker is present.

        An agent that never advertises never pays a discovery call.
        """
        if _TOOLS_MARKER not in skills:
            return self._selected_tool_catalog()

        local_catalog = self._selected_tool_catalog()
        remote_catalog = _render_remote_tool_catalog(await self._discover_remote_tools())

        if not remote_catalog:
            return local_catalog

        if not local_catalog:
            return remote_catalog

        return f"{local_catalog}\n{remote_catalog}"

    async def _discover_remote_tools(self) -> Sequence[McpTool]:
        """Best effort, and kept on success.

        A server down at discovery hides only its own tools this turn and is asked again on the
        next. The foundation has already localized and logged its failure at the severity it
        earned, so this tier degrades to no remote tools rather than failing the run.
        """
        if self._remote_tools is not None:
            return self._remote_tools

        try:
            self._remote_tools = await self.external_tool_service.retrieve_tools()

            return self._remote_tools
        except ExternalToolDependencyException:
            return ()
        except ExternalToolDependencyValidationException:
            return ()
        except ExternalToolServiceException:
            return ()


def _render_remote_tool_catalog(remote_tools: Sequence[McpTool]) -> str:
    """The remote catalog, under the rules the local one lives by.

    A description is the opt-in (SPEC.md 6.1), a run under selection is shown only what it was
    offered (SPEC.md 4.15), and the schema the server declared rides the line.
    """
    offered_tools = _offered_tools()

    catalog_lines = (
        f"- {tool.name} \u2014 {tool.description} parameters: {tool.input_schema_json}"
        for tool in remote_tools
        if tool.description and not tool.description.isspace()
        if offered_tools is None or _is_offered(tool.name, offered_tools))

    return "\n".join(catalog_lines)


def _offered_tools() -> Sequence[str] | None:
    run = AgentRun.current()

    return run.offered_tools if run is not None else None


def _is_offered(tool_name: str, offered_tools: Sequence[str]) -> bool:
    """offered.Contains(name, StringComparer.OrdinalIgnoreCase)."""
    folded_tool_name = _fold_ordinal_ignore_case(tool_name)

    return any(
        _fold_ordinal_ignore_case(offered_tool) == folded_tool_name
        for offered_tool in offered_tools)


def _fold_ordinal_ignore_case(value: str) -> str:
    """Fold a string the way .NET's StringComparer.OrdinalIgnoreCase compares it.

    Characters compare by their simple uppercase mapping. Python's str.upper() applies full
    mappings (U+00DF becomes "SS"), so each character is uppercased on its own and kept as it
    is when its mapping expands.
    """
    folded: list[str] = []

    for character in value:
        candidate = character.upper()
        folded.append(candidate if len(candidate) == 1 else character)

    return "".join(folded)


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    """Localizes the foundations' failures into the orchestration family.

    The tier above never has to know which store was behind the nature it asked for.
    """
    try:
        yield
    except (
            MemoryValidationException,
            KnowledgeValidationException,
            SessionValidationException) as validation_exception:

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, _local_exception(validation_exception))
    except (
            SkillDependencyException,
            SkillServiceException,
            MemoryDependencyException,
            MemoryServiceException,
            KnowledgeDependencyException,
            KnowledgeServiceException,
            SessionDependencyException,
            SessionServiceException) as dependency_exception:

        raise await _create_and_log_dependency_exception(
            logging_broker, _local_exception(dependency_exception))
    except Exception as exception:
        failed_agent_orchestration_service_exception = FailedAgentOrchestrationServiceException(
            message="Failed agent orchestration service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_agent_orchestration_service_exception)


def _local_exception(categorized_exception: Xeption) -> Xeption | None:
    """The foundation's local exception, the one a categorized exception wraps."""
    inner_exception = categorized_exception.inner_exception

    return inner_exception if isinstance(inner_exception, Xeption) else None


async def _create_and_log_dependency_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption | None) -> AgentOrchestrationDependencyValidationException:

    agent_orchestration_dependency_validation_exception = (
        AgentOrchestrationDependencyValidationException(
            message="Agent orchestration dependency validation error occurred, "
                    "fix the error and try again.",
            inner_exception=exception))

    await logging_broker.log_error(agent_orchestration_dependency_validation_exception)

    return agent_orchestration_dependency_validation_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Xeption | None) -> AgentOrchestrationDependencyException:

    agent_orchestration_dependency_exception = AgentOrchestrationDependencyException(
        message="Agent orchestration dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(agent_orchestration_dependency_exception)

    return agent_orchestration_dependency_exception


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> AgentOrchestrationServiceException:

    agent_orchestration_service_exception = AgentOrchestrationServiceException(
        message="Agent orchestration service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(agent_orchestration_service_exception)

    return agent_orchestration_service_exception
