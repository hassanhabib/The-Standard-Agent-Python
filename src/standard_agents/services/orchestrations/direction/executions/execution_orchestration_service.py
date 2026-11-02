# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.foundations.approvals.exceptions import (
    ApprovalDependencyException,
    ApprovalServiceException,
    ApprovalValidationException)
from standard_agents.models.foundations.effect_ledgers.exceptions import (
    EffectLedgerDependencyException,
    EffectLedgerServiceException,
    EffectLedgerValidationException)
from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyException,
    ExternalToolDependencyValidationException,
    ExternalToolServiceException,
    ExternalToolValidationException)
from standard_agents.models.foundations.internal_tools.exceptions import (
    InternalToolDependencyException,
    InternalToolServiceException,
    InternalToolValidationException)
from standard_agents.models.foundations.policies.exceptions import (
    PolicyDependencyException,
    PolicyServiceException,
    PolicyValidationException)
from standard_agents.models.foundations.returns.exceptions import (
    ReturnServiceException,
    ReturnValidationException)
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    FailedAgentOrchestrationServiceException)
from standard_agents.services.foundations.external_tools.external_tool_service import (
    ExternalToolService)
from standard_agents.services.foundations.internal_tools.internal_tool_service import (
    InternalToolService)
from standard_agents.services.foundations.returns.return_service import ReturnService
from xeptions import Xeption


class ExecutionOrchestrationService:
    """Perform it, or answer.

    The three ways an act leaves the agent: a local tool, a tool across the boundary, or the
    terminal that hands the result back and touches nothing.
    """

    def __init__(
            self,
            *,
            internal_tool_service: InternalToolService,
            external_tool_service: ExternalToolService,
            return_service: ReturnService,
            logging_broker: LoggingBroker) -> None:

        self.internal_tool_service = internal_tool_service
        self.external_tool_service = external_tool_service
        self.return_service = return_service
        self.logging_broker = logging_broker

    async def handles_locally(self, tool_name: str) -> bool:
        """True when a local tool answers to this name."""
        return await self.internal_tool_service.handles(tool_name)

    async def run(self, tool_name: str, payload: str) -> str:
        """Local first, then across the boundary. A name the agent owns is never sent outward."""
        async with _handling_exceptions(self.logging_broker):
            is_local_tool = await self.internal_tool_service.handles(tool_name)

            if is_local_tool:
                return await self.internal_tool_service.run(tool_name, payload)

            return await self.external_tool_service.call(tool_name, payload)

    async def return_payload(self, payload: str) -> str:
        return await self.return_service.return_payload(payload)

    async def compensate(self, tool_name: str, arguments: str, outcome: str) -> str:
        """Undoes a local act, or reports that it stands.

        External acts cannot be undone from here.
        """
        async with _handling_exceptions(self.logging_broker):
            if not await self.internal_tool_service.handles(tool_name):
                # Saying an external act cannot be undone is the honest answer; reporting it
                # as reversed would be worse than reporting nothing.
                return ""

            return await self.internal_tool_service.compensate(tool_name, arguments, outcome)


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except (
            PolicyValidationException,
            ApprovalValidationException,
            EffectLedgerValidationException,
            InternalToolValidationException,
            ExternalToolValidationException,
            ExternalToolDependencyValidationException,
            ReturnValidationException) as validation_exception:

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, _local_exception(validation_exception))
    except (
            PolicyDependencyException,
            PolicyServiceException,
            ApprovalDependencyException,
            ApprovalServiceException,
            EffectLedgerDependencyException,
            EffectLedgerServiceException,
            InternalToolDependencyException,
            InternalToolServiceException,
            ExternalToolDependencyException,
            ExternalToolServiceException,
            ReturnServiceException) as dependency_exception:

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
