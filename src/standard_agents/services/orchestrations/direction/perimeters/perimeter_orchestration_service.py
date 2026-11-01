# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import Enum

from standard_agents.brokers.approvals.approval_broker import ApprovalDecision
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.times.time_broker import TimeBroker
from standard_agents.models.brokers.effects.effect_state import EffectState
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
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    FailedAgentOrchestrationServiceException)
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision)
from standard_agents.models.orchestrations.effects.effect_claim import EffectClaim
from standard_agents.models.orchestrations.effects.effect_claim_verdict import (
    EffectClaimVerdict)
from standard_agents.services.foundations.approvals.approval_service import ApprovalService
from standard_agents.services.foundations.effect_ledgers.effect_ledger_service import (
    EffectLedgerService)
from standard_agents.services.foundations.policies.policy_service import PolicyService
from xeptions import Xeption


class PerimeterOrchestrationService:
    """What may cross the agent's edge: the policy, a person's approval, and the effect ledger."""

    def __init__(
            self,
            *,
            policy_service: PolicyService,
            approval_service: ApprovalService,
            effect_ledger_service: EffectLedgerService,
            time_broker: TimeBroker,
            logging_broker: LoggingBroker) -> None:

        self.policy_service = policy_service
        self.approval_service = approval_service
        self.effect_ledger_service = effect_ledger_service
        self.time_broker = time_broker
        self.logging_broker = logging_broker

    async def authorize(self, effect: AgentEffect) -> AuthorizationDecision:
        async with _handling_exceptions(self.logging_broker):
            decision = await self.policy_service.authorize_effect(effect)

            if not decision.permitted:
                await self.logging_broker.log_process(
                    "Direction",
                    f"Policy → DENIED '{effect.tool_name}': {decision.reason}")

            return decision

    async def claim(self, effect: AgentEffect) -> EffectClaim:
        """Claims the act and says what the ledger knows about it (SPEC.md 4.9).

        A completed act is replayed. A live claim by another run is told, not performed.
        Anything else (a claim past its lease, this run's own earlier attempt with no outcome, a
        failed tool, a compensation in flight or done) is an act whose fate is unknown, and the
        only honest answer is to hold the run until a person reconciles the ledger against the
        world.
        """
        async with _handling_exceptions(self.logging_broker):
            prior = await self.effect_ledger_service.claim_effect(effect)

            if prior is None:
                return EffectClaim(EffectClaimVerdict.PROCEED, outcome=None, record=None)

            if prior.state is EffectState.COMPLETED:
                await self.logging_broker.log_process(
                    "Direction",
                    f"Run-once → '{effect.tool_name}' already ran; replaying its outcome")

                return EffectClaim(
                    EffectClaimVerdict.REPLAY,
                    prior.outcome if prior.outcome is not None else "",
                    prior)

            live_elsewhere = (
                prior.state is EffectState.IN_FLIGHT
                and prior.owner != effect.run_id
                and prior.lease_until > self.time_broker.get_current_date_time())

            if live_elsewhere:
                await self.logging_broker.log_process(
                    "Direction",
                    f"Run-once → '{effect.tool_name}' is in progress in another run; "
                    "not performed")

                return EffectClaim(EffectClaimVerdict.IN_PROGRESS, outcome=None, record=prior)

            await self.logging_broker.log_process(
                "Direction",
                f"Run-once → '{effect.tool_name}' has an earlier attempt with no usable "
                f"outcome ({_enum_name(prior.state)}); held for reconciliation")

            return EffectClaim(EffectClaimVerdict.UNRECONCILED, outcome=None, record=prior)

    async def request_approval(self, effect: AgentEffect) -> ApprovalDecision:
        async with _handling_exceptions(self.logging_broker):
            approval = await self.approval_service.request_approval(effect)

            if approval is ApprovalDecision.APPROVED:
                await self.logging_broker.log_process(
                    "Direction", f"Approval → APPROVED '{effect.tool_name}'")

            return approval

    async def record_outcome(self, effect: AgentEffect, outcome: str) -> None:
        await self.effect_ledger_service.record_outcome(effect, outcome)

    async def record_failure(self, effect: AgentEffect, detail: str) -> None:
        """Records that the tool threw, so the act's unknown fate is on the record."""
        await self.effect_ledger_service.record_failure(effect, detail)

    async def release_claim(self, effect: AgentEffect) -> None:
        """Gives back the claim on an act that was held rather than performed."""
        await self.effect_ledger_service.release_claim(effect)

    async def record_compensation_intent(self, idempotency_key: str) -> None:
        await self.effect_ledger_service.record_compensation_intent(idempotency_key)

    async def record_compensation(self, idempotency_key: str, detail: str) -> None:
        await self.effect_ledger_service.record_compensation(idempotency_key, detail)


def _enum_name(value: Enum) -> str:
    """The member's name as a C# enum prints it in a string: IN_FLIGHT is InFlight."""
    return "".join(word.capitalize() for word in value.name.split("_"))


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except (
            PolicyValidationException,
            ApprovalValidationException,
            EffectLedgerValidationException,
            InternalToolValidationException,
            ExternalToolValidationException) as validation_exception:

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
            ExternalToolServiceException) as dependency_exception:

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
