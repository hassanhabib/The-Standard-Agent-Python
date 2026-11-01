# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyException,
    BrainDependencyValidationException,
    BrainServiceException,
    BrainValidationException)
from standard_agents.models.foundations.contracts.contract_verdict import ContractVerdict
from standard_agents.models.foundations.gates.exceptions import (
    GateDependencyException,
    GateDependencyValidationException,
    GateServiceException,
    GateValidationException)
from standard_agents.models.foundations.judges.exceptions import (
    JudgeDependencyException,
    JudgeDependencyValidationException,
    JudgeServiceException,
    JudgeValidationException)
from standard_agents.models.foundations.judges.judgement import Judgement
from standard_agents.models.loggings.agent_run import AgentRun
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    FailedAgentOrchestrationServiceException)
from standard_agents.services.foundations.contracts.contract_service import ContractService
from standard_agents.services.foundations.gates.gate_service import GateService
from standard_agents.services.foundations.judges.judge_service import JudgeService
from xeptions import Xeption


class GuardianOrchestrationService:
    """A conscience, before and after.

    The Gate screens what goes in and the Judge scores what comes out. They are one concept at
    two moments, which is why they share a region: the framework already calls them the
    guardians, composes one rubric for both, and Invariant 6 treats them as a single class of
    thing.
    """

    def __init__(
            self,
            *,
            gate_service: GateService,
            judge_service: JudgeService,
            contract_service: ContractService,
            logging_broker: LoggingBroker) -> None:

        self.gate_service = gate_service
        self.judge_service = judge_service
        self.contract_service = contract_service
        self.logging_broker = logging_broker

    async def screen(self, prompt: str) -> str:
        """Screens the task, once per run for the same unchanged prompt (SPEC.md 4.10).

        The prompt does not change across the turns of one run, only the observations do, so
        asking the Gate the identical question every turn is waste, not safety. What changes
        every turn is untrusted inbound (SPEC.md 4.9), and that is screened every time it
        appears. The verdict is remembered on the run, so it is evicted by the run ending.
        """
        async with _handling_exceptions(self.logging_broker):
            run = AgentRun.current()

            if run is None:
                return await self.gate_service.screen(prompt)

            cached_verdict = run.get_verdict(prompt)

            if cached_verdict is not None:
                return cached_verdict

            verdict = await self.gate_service.screen(prompt)
            run.remember_verdict(prompt, verdict)

            return verdict

    async def detect_conflict(self, instructions: str) -> str:
        """Looks for a direct contradiction across the active skill instructions."""
        async with _handling_exceptions(self.logging_broker):
            return await self.gate_service.detect_conflict(instructions)

    async def evaluate(self, task: str, candidate: str) -> Judgement:
        """Scores a draft against the task it is meant to answer (SPEC.md 4.2)."""
        async with _handling_exceptions(self.logging_broker):
            return await self.judge_service.evaluate(task, candidate)

    async def check_shape(self, answer: str, schema: str) -> ContractVerdict:
        """Checks a draft against the shape it was held to.

        The third guardian: the Gate asks whether a task may be attempted, the Judge whether a
        draft is good enough, and this whether it is the right shape. Satisfied when no contract
        is configured.
        """
        async with _handling_exceptions(self.logging_broker):
            return await self.contract_service.check(answer, schema)


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except (
            BrainValidationException,
            GateValidationException,
            JudgeValidationException,
            BrainDependencyValidationException,
            GateDependencyValidationException,
            JudgeDependencyValidationException) as validation_exception:

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, _local_exception(validation_exception))
    except (
            BrainDependencyException,
            BrainServiceException,
            GateDependencyException,
            GateServiceException,
            JudgeDependencyException,
            JudgeServiceException) as dependency_exception:

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
