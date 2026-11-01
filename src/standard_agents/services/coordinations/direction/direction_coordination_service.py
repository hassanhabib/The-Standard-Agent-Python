# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.coordinations.directions.perimeter_policy import PerimeterPolicy
from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyException,
    ExternalToolDependencyValidationException,
    ExternalToolServiceException,
    ExternalToolValidationException)
from standard_agents.models.foundations.internal_tools.exceptions import (
    InternalToolDependencyException,
    InternalToolServiceException,
    InternalToolValidationException)
from standard_agents.models.foundations.returns.exceptions import (
    ReturnServiceException,
    ReturnValidationException)
from standard_agents.models.loggings.agent_run import AgentRun
from standard_agents.models.loggings.performed_effect import PerformedEffect
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    AgentOrchestrationValidationException,
    FailedAgentOrchestrationServiceException,
    NullAgentContextException)
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.compensation_outcome import (
    CompensationOutcome)
from standard_agents.models.orchestrations.effects.effect_claim_verdict import (
    EffectClaimVerdict)
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel
from standard_agents.services.orchestrations.direction.executions.execution_orchestration_service \
    import ExecutionOrchestrationService
from standard_agents.services.orchestrations.direction.perimeters.perimeter_orchestration_service \
    import PerimeterOrchestrationService
from xeptions import Xeption

_RETURN_RESPONSE_DIRECTION = "ReturnResponse"
_REFUSE_DIRECTION = "Refuse"
_AWAIT_INPUT_DIRECTION = "AwaitInput"


class DirectionCoordinationService:
    """The Direction nature: two regions, and the order between them.

    Perimeter answers whether an act may happen; Execution performs it. Neither can own the
    sequence, because the sequence interleaves them: authorize, record the intent, approve,
    execute, record the outcome. That interleaving is Direction's own logic, which is why it lives
    in Direction's own service rather than in a generic sequencing tier.
    """

    def __init__(
            self,
            *,
            perimeter_service: PerimeterOrchestrationService,
            execution_service: ExecutionOrchestrationService,
            logging_broker: LoggingBroker,
            policy: PerimeterPolicy | None = None) -> None:
        """Two services, one utility broker, and the perimeter's standing orders as one datum.

        The orders travel in PerimeterPolicy rather than as separate parameters, three of them
        callables that take part in authorization: Policy is Data, and adding one is a reviewed
        model diff.
        """
        standing_orders = policy if policy is not None else PerimeterPolicy()

        self.permission_mode = standing_orders.mode
        self.declared_risk = standing_orders.declared_risk
        self.tool_risk = standing_orders.tool_risk
        self.tool_scope = standing_orders.tool_scope
        self.explicitly_permits = standing_orders.explicitly_permits

        # Asked once per act rather than captured once at composition, because who is acting
        # can change between prompts on the same agent (SPEC.md 4.4).
        self.identity_resolver = standing_orders.identity_resolver

        self.perimeter_service = perimeter_service
        self.execution_service = execution_service
        self.logging_broker = logging_broker
        self.irreversible_tool_names = frozenset(standing_orders.irreversible_tools)
        self.enforce_selection = standing_orders.enforce_selection
        self.advertised_tool_names = frozenset(standing_orders.advertised_tools)

    async def act(self, context: AgentContext) -> AgentContext:
        async with _handling_exceptions(self.logging_broker):
            _validate_context(context)

            if _is_terminal(context.direction_type):
                result = await self.execution_service.return_payload(context.payload)

                await self.logging_broker.log_payload(
                    "Direction", f"{context.direction_type} returned", result, detail=False)

                return dataclasses.replace(
                    context,
                    result=result,
                    status=_to_terminal_status(context.direction_type))

            return await self._act_on_effect(context)

    async def _act_on_effect(self, context: AgentContext) -> AgentContext:
        effect = AgentEffect.create(
            run_id="",
            tool_name=context.direction_type,
            arguments=context.payload,
            risk_level=self._risk_level_for(context.direction_type),
            scope=self._scope_for(context.direction_type, context.payload))

        effect = self._after_what_changed_it(context, effect)

        # 1: authorize
        decision = await self.perimeter_service.authorize(effect)

        if not decision.permitted:
            return _denied(context, decision.reason)

        # 2: record the intent, and learn what the ledger knows about this act
        claim = await self.perimeter_service.claim(effect)

        if claim.verdict is EffectClaimVerdict.REPLAY:
            outcome = claim.outcome if claim.outcome is not None else ""

            return await self._replayed_observed(context, effect, outcome)

        output = await self.execution_service.run(context.direction_type, context.payload)

        run = AgentRun.current()

        if run is not None:
            run.record_performed(
                PerformedEffect(
                    effect.tool_name,
                    effect.arguments,
                    output,
                    scope=effect.scope,
                    risk_level=effect.risk_level))

        await self.perimeter_service.record_outcome(effect, output)

        await self.logging_broker.log_payload(
            "Direction", f"Tool '{effect.tool_name}' output", output, detail=False)

        return _observed(context, output)

    async def _replayed_observed(
            self,
            context: AgentContext,
            effect: AgentEffect,
            outcome: str) -> AgentContext:
        """Once is a replay, with a note saying so.

        From the third identical ask on it is the note alone: the bytes have been handed back
        twice, and a third copy costs the person context and buys the model nothing it did not
        already have (SPEC.md 4.9, v1.14). This implementation never trims a conversation, so
        the answer the note points to is always still in view.
        """
        run = AgentRun.current()
        replays = run.record_replay(effect.idempotency_key) if run is not None else 1

        if replays < 2:
            return _observed(context, _replayed(effect.tool_name, outcome), replayed=True)

        return _observed(context, _replayed_again(effect.tool_name), replayed=True)

    def _after_what_changed_it(self, context: AgentContext, effect: AgentEffect) -> AgentEffect:
        """A look after a write to the same place is a new question (SPEC.md 4.9, v1.14).

        The ledger remembers what a read said and replays it to the same read for the rest of
        the run, which is right for an act and wrong for a look at something an act has since
        changed. So a SAFE act whose scope this run has since written to is claimed under a key
        that counts the writes: it runs, and a second identical look after the same writes
        replays as before. An act that is not SAFE keeps its key exactly: a transfer proposed
        twice is one transfer, whatever else happened in between.

        The exchanges still count, for a run resumed with a conversation: resumed, a run keeps
        its identity, so the ledger still holds the look from before the pause, and it begins
        with nothing performed. The writes before the pause are in the exchanges it was handed.
        Whichever saw more writes saw what happened.
        """
        if effect.risk_level is not RiskLevel.SAFE or not effect.scope:
            return effect

        run = AgentRun.current()
        performed_writes = run.writes_to(effect.scope) if run is not None else 0
        exchanged_writes = self._exchanged_writes_to(context, effect.scope)
        writes = max(performed_writes, exchanged_writes)

        return effect if writes == 0 else effect.after_writes(writes)

    def _exchanged_writes_to(self, context: AgentContext, scope: str) -> int:
        return sum(
            1 for exchange in context.tool_exchanges
            if self._risk_level_for(exchange.tool_name) is not RiskLevel.SAFE
            and self._scope_for(exchange.tool_name, exchange.arguments_json) == scope)

    def _risk_level_for(self, tool_name: str) -> RiskLevel:
        tool_declared = self.tool_risk.get(tool_name)

        if tool_declared is not None and tool_declared is not RiskLevel.SAFE:
            return tool_declared

        return RiskLevel.SAFE

    def _scope_for(self, tool_name: str, arguments: str) -> str:
        """What the act is about to touch, as the tool named it.

        The framework never parses arguments: only the tool knows what its own arguments mean.
        """
        scope_of = self.tool_scope.get(tool_name)

        return scope_of(arguments) if scope_of is not None else ""

    async def compensate_run(self) -> tuple[CompensationOutcome, ...]:
        """Unwinds what this run performed, in reverse order (SPEC.md 4.9).

        Reports every effect it could not undo rather than reporting the run cleanly unwound.
        """
        raise NotImplementedError


def _replayed_again(tool_name: str) -> str:
    return (
        f"[{tool_name} was asked for a third time with the same arguments. Its answer is above, "
        "from the first time, and is not repeated. Use it, ask for something different, or "
        "answer.]")


def _replayed(tool_name: str, outcome: str) -> str:
    """The same outcome, and the one thing the Brain did not already have (SPEC.md 4.9, v1.14).

    Run-once is right that the act runs once. What it hands back is the first outcome, and a
    model reading its own earlier answer back reads exactly what it was looking at when it
    decided to ask, so it decides the same thing again. The outcome comes first and whole,
    because that is the point of a replay and something downstream may be looking for a value
    inside it; the note is added after, saying only what is true.
    """
    return (
        f"{outcome}\n\n[{tool_name} already ran in this run with the same arguments, and this "
        "is what it said then. Asking again returns this same answer. Use it and do something "
        "else.]")


def _denied(context: AgentContext, reason: str) -> AgentContext:
    """A denial is non-terminal: the agent is told and may choose a permitted path next turn.

    Exactly as it recovers from a malformed call (SPEC.md 4.6, 4.9).
    """
    return dataclasses.replace(
        context,
        result=reason,
        observations=(*context.observations, f"{context.direction_type}: {reason}"))


def _with_exchange(
        context: AgentContext,
        result: str,
        replayed: bool = False) -> tuple[ToolExchange, ...]:
    """A call the model made gets an answer, whatever the answer is.

    Whether the ledger answered it rather than the tool rides with it (SPEC.md 3.2, v1.14): a
    loop that counts a run's asks has to tell a replay from a call that ran.
    """
    if not context.tool_call_id:
        return context.tool_exchanges

    return (
        *context.tool_exchanges,
        ToolExchange(
            context.tool_call_id,
            context.direction_type,
            context.payload,
            result,
            replayed=replayed))


def _observed(context: AgentContext, output: str, replayed: bool = False) -> AgentContext:
    return dataclasses.replace(
        context,
        result=output,
        observations=(*context.observations, f"{context.direction_type}: {output}"),

        # On the native path the result is also kept beside the call that asked for it, so the
        # next turn can hand it back as a tool message rather than as narration (SPEC.md 6).
        # Observations still carry it too: they are what the V0 path reads, and what the trace
        # and the Judge read on both.
        tool_exchanges=_with_exchange(context, output, replayed))


def _is_terminal(direction_type: str) -> bool:
    return direction_type in (
        _RETURN_RESPONSE_DIRECTION,
        _REFUSE_DIRECTION,
        _AWAIT_INPUT_DIRECTION)


def _to_terminal_status(direction_type: str) -> AgentStatus:
    if direction_type == _REFUSE_DIRECTION:
        return AgentStatus.REFUSED

    if direction_type == _AWAIT_INPUT_DIRECTION:
        return AgentStatus.AWAITING_INPUT

    return AgentStatus.RESPONDED


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
        # already in this family and already logged. Wrapping it again would nest and log the
        # same failure twice.
        raise
    except (
            InternalToolValidationException,
            ExternalToolValidationException,
            ExternalToolDependencyValidationException,
            ReturnValidationException) as validation_exception:

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, _local_exception(validation_exception))
    except (
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
