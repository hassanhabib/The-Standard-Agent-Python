# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.sessions.agent_session import AgentSession
from standard_agents.models.foundations.knowledges.exceptions import (
    KnowledgeDependencyException,
    KnowledgeServiceException,
    KnowledgeValidationException)
from standard_agents.models.foundations.memories.exceptions import (
    MemoryDependencyException,
    MemoryServiceException,
    MemoryValidationException)
from standard_agents.models.foundations.sessions.exceptions import (
    SessionDependencyException,
    SessionDependencyValidationException,
    SessionServiceException,
    SessionValidationException)
from standard_agents.models.foundations.skills.exceptions import (
    SkillDependencyException,
    SkillServiceException)
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    FailedAgentOrchestrationServiceException)
from standard_agents.services.foundations.memories.memory_service import MemoryService
from standard_agents.services.foundations.sessions.session_service import SessionService
from xeptions import Xeption


class RecollectionOrchestrationService:
    """What the agent accumulated, replayed.

    Memory and the session share a region because both are written by the agent's own past
    rather than by an author, and both are replayed rather than searched. Memory is what it
    learned across conversations; the session is this one.
    """

    def __init__(
            self,
            *,
            memory_service: MemoryService,
            session_service: SessionService,
            logging_broker: LoggingBroker) -> None:

        self.memory_service = memory_service
        self.session_service = session_service
        self.logging_broker = logging_broker

    async def recall_memories(self) -> Sequence[str]:
        async with _handling_exceptions(self.logging_broker):
            memories = await self.memory_service.recall_memories()

            await self.logging_broker.log_process("Data", f"Recalled {len(memories)} memories")

            return memories

    async def remember(self, memory: str) -> None:
        await self.memory_service.remember(memory)

    async def recall_session(self, session_id: str) -> AgentSession | None:
        """Loading a conversation is recall, which is why the session belongs to Data."""
        return await self.session_service.retrieve_session(session_id)

    async def record_session(self, session: AgentSession) -> None:
        await self.session_service.record_session(session)


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
            SessionValidationException,
            SessionDependencyValidationException) as validation_exception:

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
