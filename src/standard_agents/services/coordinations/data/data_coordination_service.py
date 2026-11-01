# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.brokers.sessions.agent_session import AgentSession
from standard_agents.models.foundations.knowledges.exceptions import (
    KnowledgeDependencyException,
    KnowledgeServiceException,
    KnowledgeValidationException)
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.models.foundations.memories.exceptions import (
    MemoryDependencyException,
    MemoryServiceException,
    MemoryValidationException)
from standard_agents.models.foundations.skills.exceptions import (
    SkillDependencyException,
    SkillServiceException)
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    AgentOrchestrationValidationException,
    FailedAgentOrchestrationServiceException,
    NullAgentContextException)
from standard_agents.services.orchestrations.data.recollections.recollection_orchestration_service \
    import RecollectionOrchestrationService
from standard_agents.services.orchestrations.data.retrievals.retrieval_orchestration_service \
    import RetrievalOrchestrationService
from xeptions import Xeption


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
        async with _handling_exceptions(self.logging_broker):
            _validate_context(context)

            # Announced before anything is fetched, so the trace reads in the order things
            # happened.
            await self.logging_broker.log_payload(
                "Data", "Received prompt", context.prompt, detail=False)

            system_prompt = await self.retrieval_service.retrieve_instructions(context.route)

            # The caller's vocabulary, appended per run (design 6.1). On the text protocol this
            # is the only way the model learns those words exist.
            system_prompt = _with_caller_vocabulary(system_prompt, context)

            memories = await self.recollection_service.recall_memories()
            knowledge = await self.retrieval_service.retrieve_grounding(context.prompt)
            passages = (knowledge_result.text for knowledge_result in knowledge)

            await self.logging_broker.log_payload(
                "Data", "System prompt sent to Decision", system_prompt, detail=True)

            return dataclasses.replace(
                context,
                system_prompt=system_prompt,
                observations=(*context.observations, *memories, *passages),
                grounding_sources=_with_grounding_sources(context.grounding_sources, knowledge))

    async def remember(self, memory: str) -> None:
        await self.recollection_service.remember(memory)

    async def recall_session(self, session_id: str) -> AgentSession | None:
        return await self.recollection_service.recall_session(session_id)

    async def record_session(self, session: AgentSession) -> None:
        await self.recollection_service.record_session(session)

    async def retrieve_remote_tools(self) -> Sequence[McpTool]:
        """The remote tools the agent's servers offer.

        Part of what the agent HAS, so the loop can judge them with the local tools when it
        decides what a run is offered (SPEC.md 4.15).
        """
        return await self.retrieval_service.retrieve_remote_tools()


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


def _with_caller_vocabulary(system_prompt: str, context: AgentContext) -> str:
    """The caller's tools, in the line format the tool catalog uses.

    They sit under a heading that says who executes: the model may name these words, and the
    agent never runs one. A call naming a caller tool is a terminal answer addressed to the
    caller (design 6.2).
    """
    caller_tools = context.inference.caller_tools if context.inference is not None else ()

    if not caller_tools:
        return system_prompt

    lines = (
        f"- {tool.name} — {tool.description} parameters: {tool.parameters_json}"
        for tool in caller_tools)

    return (
        system_prompt
        + "\n\nThe caller also accepts these tool calls. Invoke them exactly like tools; "
        + "the caller executes them, not you:\n"
        + "\n".join(lines))


def _validate_context(context: AgentContext | None) -> None:
    if context is None:
        raise NullAgentContextException(message="Agent context is null.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except NullAgentContextException as null_agent_context_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, null_agent_context_exception)
    except (
            AgentOrchestrationDependencyValidationException,
            AgentOrchestrationDependencyException,
            AgentOrchestrationServiceException):

        # The regions localize their own foundations' failures, so what arrives here is
        # already in this family and already logged. Wrapping it again would nest the same
        # exception twice and log it twice, telling a reader the failure happened at two tiers
        # when it happened at one.
        raise
    except (
            MemoryValidationException,
            KnowledgeValidationException) as validation_exception:

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, _local_exception(validation_exception))
    except (
            SkillDependencyException,
            SkillServiceException,
            MemoryDependencyException,
            MemoryServiceException,
            KnowledgeDependencyException,
            KnowledgeServiceException) as dependency_exception:

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


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption | None) -> AgentOrchestrationValidationException:

    agent_orchestration_validation_exception = AgentOrchestrationValidationException(
        message="Agent orchestration validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(agent_orchestration_validation_exception)

    return agent_orchestration_validation_exception


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
