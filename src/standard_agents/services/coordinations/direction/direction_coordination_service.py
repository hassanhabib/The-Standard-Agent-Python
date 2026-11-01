# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import dataclasses
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import TypeVar

from standard_agents.brokers.approvals.approval_broker import ApprovalDecision
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.effects.effect_record import EffectRecord
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
from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal
from standard_agents.models.orchestrations.effects.compensation_outcome import (
    CompensationOutcome)
from standard_agents.models.orchestrations.effects.effect_claim_verdict import (
    EffectClaimVerdict)
from standard_agents.models.orchestrations.effects.permission_mode import PermissionMode
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel
from standard_agents.services.orchestrations.direction.executions.execution_orchestration_service \
    import ExecutionOrchestrationService
from standard_agents.services.orchestrations.direction.perimeters.perimeter_orchestration_service \
    import PerimeterOrchestrationService
from xeptions import Xeption

_RETURN_RESPONSE_DIRECTION = "ReturnResponse"
_REFUSE_DIRECTION = "Refuse"
_AWAIT_INPUT_DIRECTION = "AwaitInput"

_Value = TypeVar("_Value")


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

        # Tool names compare as the C# compares them, OrdinalIgnoreCase, so every per-tool
        # mapping and set is keyed by the folded name.
        self.permission_mode = standing_orders.mode
        self.declared_risk = _by_folded_name(standing_orders.declared_risk)
        self.tool_risk = _by_folded_name(standing_orders.tool_risk)
        self.tool_scope = _by_folded_name(standing_orders.tool_scope)
        self.explicitly_permits = standing_orders.explicitly_permits

        # Asked once per act rather than captured once at composition, because who is acting
        # can change between prompts on the same agent (SPEC.md 4.4).
        self.identity_resolver = standing_orders.identity_resolver

        self.perimeter_service = perimeter_service
        self.execution_service = execution_service
        self.logging_broker = logging_broker
        self.irreversible_tool_names = frozenset(
            _fold_ordinal_ignore_case(name) for name in standing_orders.irreversible_tools)

        self.enforce_selection = standing_orders.enforce_selection

        self.advertised_tool_names = frozenset(
            _fold_ordinal_ignore_case(name) for name in standing_orders.advertised_tools)

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

            # A call naming a caller tool is not an act: it is a terminal answer addressed to
            # the caller (docs/per-request-inference.md 6.2). Classified before the perimeter,
            # because there is nothing for the perimeter to judge: the agent performs nothing.
            if _is_addressed_to_caller(context):
                return await self._await_caller(context)

            return await self._act_on_effect(context)

    async def compensate_run(self) -> tuple[CompensationOutcome, ...]:
        """Unwinds what this run performed, in reverse order (SPEC.md 4.9, Invariant 7).

        Reports every effect it could not undo rather than reporting the run cleanly unwound.
        Run-once makes an effect safe to propose twice; compensation is for the effects that
        cannot be made idempotent at all (a payment sent, a message delivered), where the only
        way back is a second, opposite act. It unwinds in reverse because a later effect may
        depend on an earlier one: undoing the booking before the payment it paid for would leave
        the payment attached to nothing.
        """
        run = AgentRun.current()

        if run is None:
            return ()

        outcomes: list[CompensationOutcome] = []

        for effect in reversed(run.performed_effects):
            outcome = await self._compensate_effect(effect)

            await self.logging_broker.log_payload(
                "Direction",
                f"Compensate '{effect.tool_name}' {'UNDONE' if outcome.undone else 'STANDS'}",
                outcome.detail,
                detail=False)

            outcomes.append(outcome)

        return tuple(outcomes)

    async def _compensate_effect(self, effect: PerformedEffect) -> CompensationOutcome:
        """Best effort per effect.

        A reversal is itself an act against the world, and acts fail; abandoning the rest
        because this one refused would leave more standing, not less.
        """
        stands = f"'{effect.tool_name}' could not be undone; the effect stands."

        try:
            # The intent goes on the record before the reversal is attempted (F-08): a process
            # that dies between the two leaves a ledger that says compensation was owed, which
            # is reconcilable, rather than one that says the act simply stands.
            await self.perimeter_service.record_compensation_intent(effect.idempotency_key)

            reversal = await self.execution_service.compensate(
                effect.tool_name, effect.arguments, effect.outcome)

            if not reversal:
                return CompensationOutcome(effect.tool_name, undone=False, detail=stands)

            await self.perimeter_service.record_compensation(effect.idempotency_key, reversal)

            return CompensationOutcome(effect.tool_name, undone=True, detail=reversal)
        except Exception:
            return CompensationOutcome(effect.tool_name, undone=False, detail=stands)

    async def _await_caller(self, context: AgentContext) -> AgentContext:
        """The run pauses; the caller must act and report back.

        The framework already models this seam, built for human approval and structurally
        identical here. The authority over this pending effect is the caller: it executes,
        posts the result on the session, and the run resumes. Same seam, different authority.
        """
        effect = dataclasses.replace(
            AgentEffect.create(
                run_id=_current_run_id(),
                tool_name=context.direction_type,
                arguments=context.payload,
                principal=self._resolve_identity()),

            # The id the model minted, preserved so the caller's result can answer it.
            call_id=context.tool_call_id)

        await self.logging_broker.log_process(
            "Direction",
            f"Caller tool '{context.direction_type}' → returned to the caller as a pending "
            "effect")

        return dataclasses.replace(
            context,
            result=f"'{context.direction_type}' is addressed to the caller; awaiting its result.",

            # The call travels with the pause, so whoever resumes can be shown the act itself
            # rather than only the news that something is waiting (SPEC.md 4.11).
            pending_effect=effect,
            status=AgentStatus.AWAITING_INPUT)

    async def _act_on_effect(self, context: AgentContext) -> AgentContext:
        """The perimeter (SPEC.md 4.9): enforcement at the boundary Direction already owned.

        In the order the spec fixes and forbids reordering: authorize, record the intent,
        approve, execute at most once, record the outcome. The order is the control.
        Authorizing after execution audits a fait accompli; recording the intent after
        execution loses the effects that crashed mid-flight; and approving after execution is
        not approval at all.
        """
        # 0: the offering (SPEC.md 4.15, enforced). Selection narrows what a run is shown; with
        # enforcement on, the offering also binds here, because a Brain outside this loop's
        # mediation can carry side-channel knowledge of the catalog and name a tool the run was
        # never shown. Caller tools never reach this method, and an undescribed tool keeps its
        # 6.1 treatment.
        if self._denied_because_selection_withheld_it(context.direction_type):
            withheld = (
                f"tool '{context.direction_type}' was not offered to this run: selection "
                "withheld it. Choose among the offered tools or answer directly.")

            await self.logging_broker.log_process(
                "Direction",
                f"Selection → DENIED '{context.direction_type}': not offered to this run")

            return _denied(context, withheld)

        effect = AgentEffect.create(
            run_id=_current_run_id(),
            tool_name=context.direction_type,
            arguments=context.payload,
            risk_level=self._risk_level_for(context.direction_type),
            approval_required=self._requires_approval(context.direction_type),
            scope=self._scope_for(context.direction_type, context.payload),

            # Who is acting, asked at the moment the act is described, so the policy deciding
            # whether it may happen is told, not merely the record written afterwards (SPEC.md
            # 4.9). None when the host configured no identity, which claims nothing rather than
            # inventing someone.
            principal=self._resolve_identity())

        effect = self._after_what_changed_it(context, effect)

        # 1: authorize
        decision = await self.perimeter_service.authorize(effect)

        if not decision.permitted:
            await self.logging_broker.log_process(
                "Direction", f"Policy → DENIED '{effect.tool_name}': {decision.reason}")

            return _denied(context, decision.reason)

        # 1b: the mode's answer for an act nothing named, under DENY. Decided here with
        # authorization and not at the approval stage, because DENY asks nobody: the act is
        # refused before its intent is recorded, exactly as a policy denial is. An act
        # RequireApproval names was mentioned, so it travels to its authority below.
        if self._denied_because_nothing_permits_it(effect):
            denial = (
                f"tool '{effect.tool_name}' is not permitted: nothing explicitly permits it "
                "and the permission mode is Deny")

            await self.logging_broker.log_process(
                "Direction",
                f"Permissions → DENIED '{effect.tool_name}': nothing explicitly permits it")

            return _denied(context, denial)

        # 2: record the intent, and learn what the ledger knows about this act
        claim = await self.perimeter_service.claim(effect)

        if claim.verdict is EffectClaimVerdict.REPLAY:
            outcome = claim.outcome if claim.outcome is not None else ""

            return await self._replayed_observed(context, effect, outcome)

        if claim.verdict is EffectClaimVerdict.IN_PROGRESS:
            return _denied(
                context,
                f"'{effect.tool_name}' is already in progress in another run; it was not "
                "performed again. Wait for that run, or answer with what you know.")

        if claim.verdict is EffectClaimVerdict.UNRECONCILED:
            return _unreconciled(context, effect, claim.record)

        # 3: approve, if required by name, or by the mode: ASK is the disposition toward
        # everything nobody mentioned, the only workable posture for an agent whose targets
        # cannot be enumerated at composition.
        if effect.approval_required or self._ask_because_nothing_permitted_it(effect):
            # A grant is remembered for the tool and the scope it was given for, exactly, so an
            # act with no named scope remembers nothing: remembering the empty scope collapsed
            # the key to the tool name, and approving a $10 transfer silently approved the
            # $10,000 one. An identical repeat is already replayed by run-once above.
            scope_is_named = bool(effect.scope)
            run = AgentRun.current()

            if scope_is_named and run is not None and run.was_granted(
                    effect.tool_name, effect.scope):

                await self.logging_broker.log_process(
                    "Direction",
                    f"Approval → already granted '{effect.tool_name}' at '{effect.scope}'")
            else:
                approval = await self.perimeter_service.request_approval(effect)

                if approval is not ApprovalDecision.APPROVED:
                    return await self._handle_unapproved(context, effect, approval)

                if scope_is_named and run is not None:
                    run.remember_grant(effect.tool_name, effect.scope)

                await self.logging_broker.log_process(
                    "Direction", f"Approval → APPROVED '{effect.tool_name}'")

        # 4: execute. A tool that throws leaves the world in an unknown state, and the ledger
        # says so: the claim is marked failed, never released, so a repeat is held rather than
        # performed blind (F-08). A cancelled tool is in that state too, as the C# catches its
        # OperationCanceledException here.
        try:
            output = await self.execution_service.run(context.direction_type, context.payload)
        except (Exception, asyncio.CancelledError) as exception:
            await self.perimeter_service.record_failure(effect, str(exception))

            raise

        # Remember that this run performed it, so it can be unwound, before the outcome is
        # recorded: the store can fail after the act succeeded, and an act that happened must
        # still be compensable. Only here: an effect denied, held, or replayed was never
        # performed by this run, and compensating it would undo something this run did not do.
        run = AgentRun.current()

        if run is not None:
            run.record_performed(
                PerformedEffect(
                    effect.tool_name,
                    effect.arguments,
                    output,
                    idempotency_key=effect.idempotency_key,
                    scope=effect.scope,
                    risk_level=effect.risk_level))

        # 5: record the outcome, before the loop advances
        await self.perimeter_service.record_outcome(effect, output)

        await self.logging_broker.log_payload(
            "Direction", f"Tool '{effect.tool_name}' input", context.payload, detail=True)

        await self.logging_broker.log_payload(
            "Direction", f"Tool '{effect.tool_name}' output", output, detail=False)

        return _observed(context, output)

    async def _handle_unapproved(
            self,
            context: AgentContext,
            effect: AgentEffect,
            approval: ApprovalDecision) -> AgentContext:
        """The act was held, not performed, so the claim taken for its intent is given back.

        Leaving it standing would make the approval unusable when it finally arrives: the
        authority says yes, the resumed run proposes the act, and the ledger reports it as
        already done (SPEC.md 4.9).
        """
        await self.perimeter_service.release_claim(effect)

        if approval is ApprovalDecision.DENIED:
            denial = f"approval denied for '{effect.tool_name}'"

            await self.logging_broker.log_process(
                "Direction", f"Approval → DENIED '{effect.tool_name}'; the claim was released")

            return _denied(context, denial)

        # Pending. The act is held, not performed: waiting is not consent (SPEC.md 4.9).
        await self.logging_broker.log_process(
            "Direction",
            f"Approval → PENDING '{effect.tool_name}'; the effect was not performed "
            "and the claim was released")

        return dataclasses.replace(
            context,
            result=f"'{effect.tool_name}' is waiting for approval before it can run.",

            # The act travels with the pause, so whoever resumes can be shown what they are
            # permitting rather than only that something is waiting (SPEC.md 4.11).
            pending_effect=effect,
            status=AgentStatus.AWAITING_APPROVAL)

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

        await self.logging_broker.log_process(
            "Direction",
            f"'{effect.tool_name}' asked for a third time with the same arguments → note only")

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
        """The host classifies first, then the tool, the only thing that knows what it does.

        The host is accountable for the deployment and can speak for tools it did not write.
        Requiring approval still implies IRREVERSIBLE when nobody said otherwise: that is what
        it meant before, and a list written against an earlier release keeps its meaning.
        """
        folded_tool_name = _fold_ordinal_ignore_case(tool_name)
        host_declared = self.declared_risk.get(folded_tool_name)

        if host_declared is not None:
            return host_declared

        tool_declared = self.tool_risk.get(folded_tool_name)

        if tool_declared is not None and tool_declared is not RiskLevel.SAFE:
            return tool_declared

        if folded_tool_name in self.irreversible_tool_names:
            return RiskLevel.IRREVERSIBLE

        return RiskLevel.SAFE

    def _scope_for(self, tool_name: str, arguments: str) -> str:
        """What the act is about to touch, as the tool named it.

        The framework never parses arguments: only the tool knows what its own arguments mean.
        """
        scope_of = self.tool_scope.get(_fold_ordinal_ignore_case(tool_name))

        return scope_of(arguments) if scope_of is not None else ""

    def _requires_approval(self, tool_name: str) -> bool:
        return _fold_ordinal_ignore_case(tool_name) in self.irreversible_tool_names

    def _resolve_identity(self) -> AgentPrincipal | None:
        return self.identity_resolver() if self.identity_resolver is not None else None

    def _ask_because_nothing_permitted_it(self, effect: AgentEffect) -> bool:
        """The mode speaks only for what the explicit permissions did not mention.

        An allow-list that names the tool has already answered the question, and asking anyway
        would make the list meaningless.
        """
        return (
            self.permission_mode is PermissionMode.ASK
            and not self._is_explicitly_permitted(effect))

    def _denied_because_nothing_permits_it(self, effect: AgentEffect) -> bool:
        """DENY's twin of the ASK predicate, sharing its reading of "explicitly permitted".

        An allow-list entry names the act, and a RequireApproval name routes it to an authority
        instead. Everything else is refused.
        """
        return (
            self.permission_mode is PermissionMode.DENY
            and not effect.approval_required
            and not self._is_explicitly_permitted(effect))

    def _is_explicitly_permitted(self, effect: AgentEffect) -> bool:
        return self.explicitly_permits is not None and self.explicitly_permits(effect)

    def _denied_because_selection_withheld_it(self, tool_name: str) -> bool:
        """Enforcement speaks only where selection spoke.

        A run with no recorded offering (no selector configured) has nothing to enforce, and a
        name selection never saw (undescribed, 6.1) is not selection's to withhold.
        """
        run = AgentRun.current()

        if not self.enforce_selection or run is None or run.offered_tools is None:
            return False

        return self._is_advertised(tool_name, run) and not any(
            _equals_ignoring_case(offered_tool, tool_name) for offered_tool in run.offered_tools)

    def _is_advertised(self, tool_name: str, run: AgentRun) -> bool:
        """What selection could have offered.

        The agent's described tools, and the described remote tools this run discovered.
        Enforcement used to check the local set alone, so an unoffered remote call went through
        (principal review 2026-09-04, F-04).
        """
        if _fold_ordinal_ignore_case(tool_name) in self.advertised_tool_names:
            return True

        return any(
            remote_tool.description
            and not remote_tool.description.isspace()
            and _equals_ignoring_case(remote_tool.name, tool_name)
            for remote_tool in run.remote_tools)


def _is_addressed_to_caller(context: AgentContext) -> bool:
    """The boundary already dropped any caller tool sharing a configured name.

    So a name found here has exactly one meaning: the caller's.
    """
    if context.inference is None:
        return False

    return any(
        _equals_ignoring_case(caller_tool.name, context.direction_type)
        for caller_tool in context.inference.caller_tools)


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


def _current_run_id() -> str:
    run = AgentRun.current()

    return run.id if run is not None else ""


def _unreconciled(
        context: AgentContext,
        effect: AgentEffect,
        record: EffectRecord) -> AgentContext:
    """An earlier attempt whose fate is unknown ends the turn waiting on the caller.

    The act travels as the pending effect, key included, so whoever holds the ledger can check
    the world, record the real outcome or release the claim, and resume (SPEC.md 4.9, 4.11).
    Performing it blind could do it twice; presuming it done could leave it never done.
    """
    return dataclasses.replace(
        context,
        result=(
            f"'{effect.tool_name}' has an earlier attempt in the ledger with no usable outcome "
            f"(state: {_enum_name(record.state)}, claimed {_universal_sortable(record.claimed_on)}"
            "); reconcile the ledger against the world - record the real outcome, or release "
            "the claim - before this act can run again."),
        pending_effect=effect,
        status=AgentStatus.AWAITING_INPUT)


def _enum_name(value: Enum) -> str:
    """The member's name as a C# enum prints it in a string: IN_FLIGHT is InFlight."""
    return "".join(word.capitalize() for word in value.name.split("_"))


def _universal_sortable(moment: datetime) -> str:
    """The moment as .NET's "u" format prints a DateTimeOffset: in UTC, 2026-11-01 18:30:00Z.

    Formatted field by field, because strftime does not zero-pad a year before 1000 on every
    platform, and an unclaimed record carries DateTimeOffset.MinValue.
    """
    utc = moment.astimezone(timezone.utc)

    return (
        f"{utc.year:04d}-{utc.month:02d}-{utc.day:02d} "
        f"{utc.hour:02d}:{utc.minute:02d}:{utc.second:02d}Z")


def _denied(context: AgentContext, reason: str) -> AgentContext:
    """A denial is non-terminal: the agent is told and may choose a permitted path next turn.

    Exactly as it recovers from a malformed call (SPEC.md 4.6, 4.9).
    """
    return dataclasses.replace(
        context,
        result=reason,
        observations=(*context.observations, f"{context.direction_type}: {reason}"),
        tool_exchanges=_with_exchange(context, reason),
        status=AgentStatus.WORKING)


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
        tool_exchanges=_with_exchange(context, output, replayed),

        status=AgentStatus.WORKING)


def _is_terminal(direction_type: str) -> bool:
    return (
        _equals_ignoring_case(direction_type, _RETURN_RESPONSE_DIRECTION)
        or _equals_ignoring_case(direction_type, _REFUSE_DIRECTION)
        or _equals_ignoring_case(direction_type, _AWAIT_INPUT_DIRECTION))


def _to_terminal_status(direction_type: str) -> AgentStatus:
    if _equals_ignoring_case(direction_type, _REFUSE_DIRECTION):
        return AgentStatus.REFUSED

    if _equals_ignoring_case(direction_type, _AWAIT_INPUT_DIRECTION):
        return AgentStatus.AWAITING_INPUT

    return AgentStatus.RESPONDED


def _by_folded_name(entries: Mapping[str, _Value]) -> dict[str, _Value]:
    """A per-tool mapping keyed as StringComparer.OrdinalIgnoreCase keys it."""
    return {_fold_ordinal_ignore_case(name): value for name, value in entries.items()}


def _equals_ignoring_case(left: str, right: str) -> bool:
    """string.Equals(left, right, StringComparison.OrdinalIgnoreCase)."""
    return _fold_ordinal_ignore_case(left) == _fold_ordinal_ignore_case(right)


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
