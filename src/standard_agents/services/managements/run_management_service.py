# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import dataclasses
import itertools
from collections.abc import AsyncIterator, Callable, Iterable, Mapping, Sequence
from contextlib import aclosing, asynccontextmanager, nullcontext
from datetime import datetime
from typing import TypeVar

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.telemetries.not_configured_telemetry_broker import (
    NotConfiguredTelemetryBroker)
from standard_agents.brokers.telemetries.telemetry_broker import TelemetryBroker
from standard_agents.brokers.times.system_time_broker import SystemTimeBroker
from standard_agents.brokers.times.time_broker import TimeBroker
from standard_agents.models.brokers.generators.provider_options import ProviderOptions
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import ToolDefinition
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.brokers.sessions.agent_session import AgentSession
from standard_agents.models.clients.agents.agent_failure import AgentFailure
from standard_agents.models.clients.agents.agent_failure_category import AgentFailureCategory
from standard_agents.models.clients.agents.agent_failure_codes import AgentFailureCodes
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_run_stream import AgentRunStream
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.coordinations.agents.agent_budget import AgentBudget
from standard_agents.models.coordinations.agents.agent_spend import AgentSpend
from standard_agents.models.coordinations.agents.exceptions import (
    AgentCoordinationDependencyException,
    AgentCoordinationDependencyValidationException,
    AgentCoordinationValidationException,
    FailedRunManagementServiceException,
    InvalidAgentException,
    RunManagementServiceException)
from standard_agents.models.coordinations.agents.principal_resolver import PrincipalResolver
from standard_agents.models.coordinations.agents.tool_narration import ToolNarration
from standard_agents.models.coordinations.agents.tool_selector import ToolSelector
from standard_agents.models.foundations.usages.agent_usage import AgentUsage
from standard_agents.models.loggings.agent_run import AgentRun
from standard_agents.models.loggings.agent_step import AgentStep
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    AgentOrchestrationValidationException)
from standard_agents.services.coordinations.data.data_coordination_service import (
    DataCoordinationService)
from standard_agents.services.coordinations.decision.decision_coordination_service import (
    DecisionCoordinationService)
from standard_agents.services.coordinations.decision.decision_stream import DecisionStream
from standard_agents.services.coordinations.direction.direction_coordination_service import (
    DirectionCoordinationService)
from standard_agents.services.managements._budgets import (
    CANCELLED_MESSAGE,
    COST_BUDGET_MESSAGE,
    TIME_BUDGET_MESSAGE,
    TOKEN_BUDGET_MESSAGE,
    circles_message,
    stopped_failure)
from standard_agents.services.managements._citations import is_citing_knowledge, with_citations
from standard_agents.services.managements._run_events import RunEvents
from standard_agents.services.managements._screening import is_refusal, withheld
from standard_agents.services.managements._sessions import (
    checkpoint,
    completed,
    is_stale_session_write,
    resumed_run_id)
from standard_agents.services.managements._text import (
    fold,
    is_blank,
    replace_line_endings,
    trim)
from xeptions import Xeption

_DEFAULT_MAX_TURNS = 7

_RETRIES_EXHAUSTED_MESSAGE = "I can't help with that at the moment."

_TURNS_EXHAUSTED_MESSAGE = (
    "I ran out of turns before an answer was ready; nothing was delivered.")

# Above the default turn cap, so a composition that never set it is bounded by the turn cap
# exactly as before (SPEC.md 4.10, v1.14).
_DEFAULT_IDENTICAL_CALL_LIMIT = 8

_DEFAULT_KNOWLEDGE_CITATION_PREFIX = "Source: "

# Bounded, because a store that refuses every write is an outage, not contention.
_MAX_SESSION_WRITE_ATTEMPTS = 16

_Value = TypeVar("_Value")

# The statuses that end a turn with words for the caller, when there are words.
_ANSWERING_STATUSES = (
    AgentStatus.RESPONDED,
    AgentStatus.REFUSED,
    AgentStatus.AWAITING_INPUT,
    AgentStatus.AWAITING_APPROVAL)


class RunManagementService:
    """The run: Data, Decision and Direction, turn after turn, until the agent has an answer.

    One loop, read through four doors: the answer (process_prompt), how the run ended (run),
    the run's events as they happen (process_prompt_stream), and both at once (run_stream).
    It is deliberately the only copy of the loop (SPEC.md 7.6): two loops that must agree is a
    discipline, one loop is a fact. Exactly two things differ between the doors, and both are
    named in the loop: which Brain protocol Decision drives, and whether anybody reads the
    events.
    """

    def __init__(
            self,
            *,
            data_coordination_service: DataCoordinationService,
            decision_coordination_service: DecisionCoordinationService,
            direction_coordination_service: DirectionCoordinationService,
            logging_broker: LoggingBroker,
            max_turns: int = _DEFAULT_MAX_TURNS,
            time_broker: TimeBroker | None = None,
            budget: AgentBudget | None = None,
            max_history_turns: int = 20,
            compensate_on_failure: bool = False,
            screen_tool_output: bool = False,
            telemetry_broker: TelemetryBroker | None = None,
            contract_schema: str | None = None,
            configured_temperature: float | None = None,
            configured_max_tokens: int | None = None,
            configured_tool_names: Iterable[str] | None = None,
            tool_narrations: Mapping[str, ToolNarration] | None = None,
            tool_selector: ToolSelector | None = None,
            described_tool_names: Iterable[str] | None = None,
            principal_resolver: PrincipalResolver | None = None,
            identical_call_limit: int = _DEFAULT_IDENTICAL_CALL_LIMIT,
            configured_cite_knowledge: bool | None = None,
            knowledge_citation_prefix: str = _DEFAULT_KNOWLEDGE_CITATION_PREFIX) -> None:

        self.data_coordination_service = data_coordination_service
        self.decision_coordination_service = decision_coordination_service
        self.direction_coordination_service = direction_coordination_service
        self.logging_broker = logging_broker
        self.max_turns = max_turns
        self.time_broker = time_broker if time_broker is not None else SystemTimeBroker()
        self.budget = budget
        self.max_history_turns = max_history_turns
        self.compensate_on_failure = compensate_on_failure

        # What may enter the context between turns is the loop's question, so the loop asks
        # Decision, which owns the Gate.
        self.screen_tool_output = screen_tool_output

        self.telemetry_broker = (
            telemetry_broker if telemetry_broker is not None
            else NotConfiguredTelemetryBroker())

        # What the deployment established, kept so precedence can be resolved at the top of each
        # run. None means the host expressed no opinion, which is exactly what lets a request's
        # value take effect (docs/per-request-inference.md 4.2).
        self.contract_schema = contract_schema
        self.configured_temperature = configured_temperature
        self.configured_max_tokens = configured_max_tokens

        # Tool names compare as the C# compares them, OrdinalIgnoreCase, so the configured names
        # and the declared narrations are keyed by the folded name.
        self.configured_tool_names = frozenset(
            fold(name) for name in configured_tool_names or ())

        # What the tools declared they say, keyed by tool name: derived data, like risk and
        # scope, so the loop can voice acts without holding the tools.
        self.tool_narrations = {
            fold(name): narration for name, narration in (tool_narrations or {}).items()}

        # Selection (SPEC.md 4.15): the host's judgment of what a run is OFFERED, and the
        # described names it judges over. No selector means every described tool is offered.
        self.tool_selector = tool_selector
        self.described_tool_names = tuple(described_tool_names or ())

        # Who is acting, when the host says (SPEC.md 4.9): what a session records as its owner,
        # and what a session another principal opened is refused against.
        self.principal_resolver = principal_resolver

        self.identical_call_limit = identical_call_limit

        # Citation (SPEC.md 4.2): what the deployment configured, None when it expressed no
        # opinion, and what each citation line starts with.
        self.configured_cite_knowledge = configured_cite_knowledge
        self.knowledge_citation_prefix = knowledge_citation_prefix

    async def process_prompt(
            self,
            prompt: str,
            *,
            session_id: str = "",
            cancellation: asyncio.Event | None = None) -> str:
        """The run's answer, or the reason there is not one.

        A plain prompt is a request that expressed no opinions: one path, not a simple mode and
        an advanced one, which is what keeps every control identical on both. Setting
        cancellation asks the run to stop at its next turn boundary; it then ends normally and
        says it was cancelled (SPEC.md 4.10).
        """
        outcome = await self._run(
            PromptRequest(prompt=prompt, session_id=session_id),
            cancellation)

        return outcome.result

    async def run(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AgentOutcome:
        """The run asked for by a request, reported with how it ended.

        An exposer cannot do without this: a run that ended AWAITING_INPUT holding a caller's
        tool call and a run that answered read alike as strings. Precedence is resolved once at
        the top of the run (docs/per-request-inference.md).
        """
        return await self._run(request, cancellation)

    def process_prompt_stream(
            self,
            prompt: str,
            *,
            session_id: str = "",
            cancellation: asyncio.Event | None = None) -> AsyncIterator[AgentStreamEvent]:
        """The run's events as they happen, as an async generator.

        Every control the batched door enforces (budgets, cancellation, sessions) holds here
        too: a control a caller can step around by changing method is not a control
        (SPEC.md 7.6, 4.10, 4.11).
        """
        return self._mapped_stream(
            PromptRequest(prompt=prompt, session_id=session_id),
            lambda _: None,
            cancellation)

    def run_stream(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AgentRunStream:
        """The run's events as they happen, and how it ended once they are read (SPEC.md 4.14).

        One run, two readings: never a choice between the answer's structure and the run's
        story.
        """
        return AgentRunStream(
            lambda set_outcome: self._mapped_stream(request, set_outcome, cancellation))

    async def _run(
            self,
            request: PromptRequest,
            cancellation: asyncio.Event | None) -> AgentOutcome:
        """The batched reading of the one loop: drain the events, keep how it ended."""
        async with _handling_exceptions(self.logging_broker):
            outcome = AgentOutcome("", AgentStatus.FAILED)

            def set_outcome(ended: AgentOutcome) -> None:
                nonlocal outcome
                outcome = ended

            run_events = self._run_core(
                request,
                streaming=False,
                set_outcome=set_outcome,
                cancellation=cancellation)

            async with aclosing(run_events):
                async for _ in run_events:
                    pass

            return outcome

    async def _mapped_stream(
            self,
            request: PromptRequest,
            set_outcome: Callable[[AgentOutcome], None],
            cancellation: asyncio.Event | None) -> AsyncIterator[AgentStreamEvent]:
        """The streamed reading, with the same exception mapping the batched door gets.

        A generator cannot wrap its yields in the mapping, but the failure points are the
        awaits, not the yields, so the enumeration advances inside the mapping and yields
        outside it. asyncio.CancelledError passes through unmapped: the caller cancelled and
        gets the cancellation, not a service error.
        """
        run_events = self._run_core(
            request,
            streaming=True,
            set_outcome=set_outcome,
            cancellation=cancellation)

        async with aclosing(run_events):
            while True:
                try:
                    streamed = await anext(run_events)
                except StopAsyncIteration:
                    break
                except Exception as exception:
                    raise await _mapped_and_logged(self.logging_broker, exception)

                yield streamed

    async def _run_core(
            self,
            request: PromptRequest,
            *,
            streaming: bool,
            set_outcome: Callable[[AgentOutcome], None],
            cancellation: asyncio.Event | None) -> AsyncIterator[AgentStreamEvent]:
        """The seam between the one loop and its doors: the loop runs in a task of its own.

        The run's identity is ambient (AgentRun is a ContextVar) and a generator has no context
        of its own: a run begun inside one would be the reader's current run between events, and
        whatever the reader set would reach the run. A task runs in its own copy of the context,
        so the loop owns the run and writes its events to RunEvents, and this generator only
        reads and yields. A cancelled run still owes its final Status events, so the reading
        continues until the loop completes the events; only a reader that stops reading
        abandons them.
        """
        run_events = RunEvents()

        pump = asyncio.create_task(
            self._pump_run(request, streaming, run_events, set_outcome, cancellation))

        try:
            async for streamed in run_events:
                yield streamed
        except asyncio.CancelledError:
            # task.cancel() keeps its ordinary meaning: the reader's cancellation stops the run's
            # work too, wherever it is.
            pump.cancel()

            raise
        finally:
            run_events.abandon()

            # Awaited without raising: the run's fault already surfaced through the events, and
            # this only keeps an abandoned run from going unobserved.
            await asyncio.wait({pump})

            if not pump.cancelled():
                pump.exception()

    async def _pump_run(
            self,
            request: PromptRequest,
            streaming: bool,
            run_events: RunEvents,
            set_outcome: Callable[[AgentOutcome], None],
            cancellation: asyncio.Event | None) -> None:

        try:
            await self._run_the_loop(request, streaming, run_events, set_outcome, cancellation)
        except BaseException as exception:
            await run_events.complete(exception)

            raise

        await run_events.complete()

    async def _run_the_loop(
            self,
            request: PromptRequest,
            streaming: bool,
            run_events: RunEvents,
            set_outcome: Callable[[AgentOutcome], None],
            cancellation: asyncio.Event | None) -> None:

        _validate_prompt(request.prompt)

        prompt = request.prompt
        session_id = request.session_id

        # Read before the run begins: a session that never delivered an answer was interrupted,
        # and the next prompt in it continues that run rather than starting a fresh one.
        session = await self._peek_session(session_id)

        # This prompt's run (SPEC.md 4.4): one instance serves prompts concurrently, and each
        # invocation establishes its own identity, so everything recorded below is credited to
        # this run and to no other. The run scope opens beside it and closes with it, so every
        # turn span lands inside it; None when nothing is listening.
        with AgentRun.begin(resumed_run_id(session), cancellation):
            with self.telemetry_broker.start_run(session_id) or nullcontext():
                run = AgentRun.current()

                # The prompt rides the run, so a handoff template's {prompt} can ground a
                # sub-agent in the real goal (SPEC.md 6.1).
                run.prompt = prompt

                await self.logging_broker.log_reset()
                await self._announce_resolution(request)

                # Resolved once, at the top, like every other request field: two turns of one
                # run never disagree about whether its answer is cited (SPEC.md 4.2).
                citing_knowledge = is_citing_knowledge(self.configured_cite_knowledge, request)

                await self._offer_tools(prompt, run)

                # The caller-owned transcript seeds the run; a session, when one exists,
                # overwrites the history below: the deployment's record of the conversation
                # beats the caller's retelling of it (docs/per-request-inference.md 4).
                context = AgentContext(
                    prompt=prompt,
                    session_id=session_id,
                    history=request.history,
                    tool_exchanges=request.tool_exchanges,
                    inference=self._resolve(request))

                # The start-of-run checkpoint, written before any work is done (SPEC.md 4.11),
                # and the conversation so far, loaded before Decision runs so the Brain sees it.
                await self._begin_session(context)
                context = await self._load_session(context, session)

                set_outcome(await self._turn_after_turn(
                    context, run, streaming, run_events, citing_knowledge, cancellation))

    async def _turn_after_turn(
            self,
            context: AgentContext,
            run: AgentRun,
            streaming: bool,
            run_events: RunEvents,
            citing_knowledge: bool,
            cancellation: asyncio.Event | None) -> AgentOutcome:

        # Budgets and cancellation are both checked at the turn boundary (SPEC.md 4.10): a turn
        # is the smallest unit the loop can stop between without abandoning work mid-flight, in
        # particular without leaving an effect half-recorded.
        spend = AgentSpend()
        started_on = self.time_broker.get_current_date_time()
        stopped_because: str | None = None

        # AgentSpend keeps one number because the budget bounds one number; telemetry reports
        # input and output apart because that is how a collector prices and reasons about them.
        # One estimate in the sum makes the sum an estimate (SPEC.md 3.4).
        run_usage = AgentUsage.EMPTY

        for turn in range(self.max_turns):
            stopped_because = self._stopped_because(spend, started_on, cancellation)

            if stopped_because is not None:
                break

            # Scoped to the iteration: continue and break both close the turn span.
            with self.telemetry_broker.start_turn(turn) or nullcontext():
                await self.logging_broker.log_turn(turn)

                await self.logging_broker.log_step(AgentStep.DATA)
                context = await self._recall_or_unwind(context)

                await self.logging_broker.log_step(AgentStep.DECISION)
                context = await self._think(context, streaming, run_events)

                spend.add_tokens(context.prompt_tokens, context.completion_tokens)

                run_usage = AgentUsage(
                    prompt_tokens=run_usage.prompt_tokens + context.prompt_tokens,
                    completion_tokens=run_usage.completion_tokens + context.completion_tokens,
                    is_estimated=run_usage.is_estimated or context.usage_is_estimated)

                self.telemetry_broker.record_turn_usage(
                    context.prompt_tokens, context.completion_tokens, context.usage_is_estimated)

                # What the run has spent so far, said the moment it is known (SPEC.md 4.14.1):
                # the count the budget reads, not a second one. Before a revision's continue,
                # because a draft sent back was still written.
                await run_events.write(AgentStreamEvent(
                    AgentStreamEventType.USAGE, str(run_usage.total_tokens), usage=run_usage))

                if context.status is AgentStatus.REVISING:
                    await self.logging_broker.log_outcome(f"turn {turn}: revising")

                    continue

                await self.logging_broker.log_step(AgentStep.DIRECTION)

                # Voiced before the act it announces, screened first (SPEC.md Invariant 5).
                await self._voice_narration(context, run_events)

                # Cleared before the act, so a transfer below reads how THIS act ended and never
                # a handoff from an earlier turn.
                run.handoff_outcome = None

                # Screened before the Tool event below: a caller watching the stream must not
                # receive the text the Brain was protected from (SPEC.md 4.9).
                observed_before = len(context.observations)

                context = await self._act_or_unwind(context)
                context = await self._screened_or_unwind(context, observed_before)

                # A transfer is terminal by meaning: the specialist's answer IS the answer. It is
                # adopted only when the specialist actually responded; a handoff that was held,
                # refused or failed stays an observation, and the loop keeps working the task.
                if (context.transferring
                        and context.status is AgentStatus.WORKING
                        and run.handoff_outcome is not None
                        and run.handoff_outcome.status is AgentStatus.RESPONDED):

                    context = dataclasses.replace(context, status=AgentStatus.RESPONDED)

                # After the Judge, before the Response event and the session write, so every
                # door carries the one cited answer (SPEC.md 4.2).
                if citing_knowledge:
                    context = with_citations(context, self.knowledge_citation_prefix)

                await self.logging_broker.log_outcome(
                    f"turn {turn}: {_status_name(context.status)}")

                await self._deliver(context, run_events)

                if context.status is not AgentStatus.WORKING:
                    break

        if stopped_because is not None:
            return await self._stopped(context, stopped_because, run_events, run_usage)

        if context.status is AgentStatus.WORKING:
            return await self._out_of_turns(context, run_events, run_usage)

        return await self._concluded(context, run_events, run_usage)

    async def _think(
            self,
            context: AgentContext,
            streaming: bool,
            run_events: RunEvents) -> AgentContext:
        """One turn of thought, on the Brain protocol of the door the run entered by.

        A host's generator sees on each door the calls it always saw.
        """
        if not streaming:
            return await self._thought_or_unwind(context)

        decision_stream = self.decision_coordination_service.think_stream(context)

        async with aclosing(self._unwound_on_fault(decision_stream)) as decision_events:
            async for decision_event in decision_events:
                await run_events.write(decision_event)

        return decision_stream.result

    async def _deliver(self, context: AgentContext, run_events: RunEvents) -> None:
        if context.status is AgentStatus.WORKING and context.result:
            await self._voice_observed_narration(context, run_events)

            await run_events.write(AgentStreamEvent(
                AgentStreamEventType.TOOL, f"{context.direction_type}: {context.result}"))

        # A held act is announced before its message: the Status event says WHAT happened for a
        # consumer that switches on kinds, and the Response carries the same words the batched
        # caller receives, so filtering a stream to Response equals what process_prompt returns.
        if context.status is AgentStatus.AWAITING_APPROVAL:
            await run_events.write(AgentStreamEvent(
                AgentStreamEventType.STATUS, "an act is waiting for approval; the run is held"))

        if context.status in _ANSWERING_STATUSES and context.result:
            await run_events.write(
                AgentStreamEvent(AgentStreamEventType.RESPONSE, context.result))

    async def _stopped(
            self,
            context: AgentContext,
            stopped_because: str,
            run_events: RunEvents,
            run_usage: AgentUsage) -> AgentOutcome:
        """Cancelled, out of budget, or going in circles.

        Reported as a Status rather than a Response, because it is not an answer, and never
        remembered or written back as one: the next prompt would otherwise be told the agent
        said something it never said (SPEC.md 4.10, 4.11).
        """
        await self.logging_broker.log_outcome(f"stopped: {stopped_because}")
        await run_events.write(AgentStreamEvent(AgentStreamEventType.STATUS, stopped_because))
        context = dataclasses.replace(context, status=AgentStatus.FAILED)

        # A run that stopped without delivering an answer may have left effects behind
        # (SPEC.md 4.9); the caller is told what was unwound and what stood.
        stopped_unwound = await self._unwind()

        if stopped_unwound:
            await run_events.write(
                AgentStreamEvent(AgentStreamEventType.STATUS, stopped_unwound))

        await self.logging_broker.log_outcome(f"done: {_status_name(context.status)}")

        self.telemetry_broker.record_run_outcome(
            _status_name(context.status), run_usage.prompt_tokens, run_usage.completion_tokens)

        stopped_result = (
            f"{stopped_because} {stopped_unwound}" if stopped_unwound else stopped_because)

        return AgentOutcome(
            stopped_result,
            AgentStatus.FAILED,
            failure=stopped_failure(stopped_because, stopped_result, self._circles_message))

    async def _out_of_turns(
            self,
            context: AgentContext,
            run_events: RunEvents,
            run_usage: AgentUsage) -> AgentOutcome:
        """Turns ran out with the loop still WORKING: no answer was ever delivered.

        The last tool output is not one. The same truth the budget stop tells, told the same
        way, and no session write, so the next prompt resumes the interrupted run. The status
        stays WORKING: the run stopped mid-work (SPEC.md 4.10, 4.11).
        """
        await self.logging_broker.log_outcome(f"stopped: {_TURNS_EXHAUSTED_MESSAGE}")

        await run_events.write(
            AgentStreamEvent(AgentStreamEventType.STATUS, _TURNS_EXHAUSTED_MESSAGE))

        capped_unwound = await self._unwind()

        if capped_unwound:
            await run_events.write(AgentStreamEvent(AgentStreamEventType.STATUS, capped_unwound))

        await self.logging_broker.log_outcome(f"done: {_status_name(context.status)}")

        # Working, not Responded: the run stopped mid-work, and the span says so the same way
        # the caller is told.
        self.telemetry_broker.record_run_outcome(
            _status_name(context.status), run_usage.prompt_tokens, run_usage.completion_tokens)

        capped_result = (
            f"{_TURNS_EXHAUSTED_MESSAGE} {capped_unwound}" if capped_unwound
            else _TURNS_EXHAUSTED_MESSAGE)

        # With the code that says why, beside the status that says it stopped mid-work
        # (SPEC.md 3.6, v1.14).
        return AgentOutcome(
            capped_result,
            context.status,
            failure=AgentFailure(
                AgentFailureCategory.SERVICE, AgentFailureCodes.TURNS_EXHAUSTED, capped_result))

    async def _concluded(
            self,
            context: AgentContext,
            run_events: RunEvents,
            run_usage: AgentUsage) -> AgentOutcome:

        if context.status is AgentStatus.REVISING:
            await run_events.write(AgentStreamEvent(
                AgentStreamEventType.STATUS, "unable to satisfy review after retries; refusing"))

            await run_events.write(
                AgentStreamEvent(AgentStreamEventType.RESPONSE, _RETRIES_EXHAUSTED_MESSAGE))

            context = dataclasses.replace(
                context,
                result=_RETRIES_EXHAUSTED_MESSAGE,
                status=AgentStatus.REFUSED)

        await self.logging_broker.log_outcome(f"done: {_status_name(context.status)}")

        if context.remember:
            await self.data_coordination_service.remember(context.remember)

        # Appended before the run ends, so the next prompt sees it (SPEC.md 4.11).
        await self._save_session(context, is_completed=True)

        self.telemetry_broker.record_run_outcome(
            _status_name(context.status), run_usage.prompt_tokens, run_usage.completion_tokens)

        # The pending effect rides the outcome as well as the session (SPEC.md 4.11): a
        # stateless deployment has no session, and an exposer that cannot reach the pending
        # call cannot yield it to the caller (docs/per-request-inference.md 6.2).
        return AgentOutcome(context.result, context.status, context.pending_effect)

    async def _offer_tools(self, prompt: str, run: AgentRun) -> None:
        """What this run is OFFERED (SPEC.md 4.15), resolved once and carried on the run.

        The offering is rendered two tiers below (the text catalog and the native tool list),
        and neither renderer should gain a parameter for it. What the agent's servers offer is
        discovered here too, so selection judges remote tools with the local ones; a double that
        answered nothing is no servers. Recorded, because a review of a run that lacked a
        capability must see that it was withheld by selection rather than missing.
        """
        remote_tools = tuple(await self.data_coordination_service.retrieve_remote_tools() or ())
        described_tool_names = self._described_tool_names(remote_tools)
        run.remote_tools = remote_tools

        if self.tool_selector is None:
            return

        chosen = {fold(name) for name in await self.tool_selector.select(
            prompt, described_tool_names)}

        # Names the agent does not carry are ignored, and the record states the TRUTH of the
        # offering, never the selector's claim (SPEC.md 4.15).
        offered = tuple(name for name in described_tool_names if fold(name) in chosen)
        run.offered_tools = offered

        await self.logging_broker.log_process(
            "Run",
            f"Selection → offered [{', '.join(offered)}]; withheld "
            f"[{', '.join(_except(described_tool_names, offered))}]")

    def _described_tool_names(self, remote_tools: Sequence[McpTool]) -> tuple[str, ...]:
        """The agent's own described names, then its servers'.

        A description is the opt-in for both (SPEC.md 6.1), and a remote name the agent already
        carries locally is the local tool's: first to claim a name keeps it.
        """
        local_names = {fold(name) for name in self.described_tool_names}

        remote_described_tool_names = tuple(
            tool.name for tool in remote_tools
            if not is_blank(tool.description) and fold(tool.name) not in local_names)

        return (*self.described_tool_names, *remote_described_tool_names)

    def _resolve(self, request: PromptRequest) -> ResolvedInference:
        """Precedence, per field: configured, then request, then framework default.

        What is established and hard-configured takes precedence, always: a caller can never
        widen the boundary the deployment set. The request's schema is never merged and never
        partially honored: one schema survives, and it seeds the wire and the guardian alike
        (docs/per-request-inference.md 4, 4.1).
        """
        return ResolvedInference(
            temperature=_first_opinion(
                self.configured_temperature,
                request.temperature,
                ResolvedInference.DEFAULT_TEMPERATURE),

            max_tokens=_first_opinion(
                self.configured_max_tokens,
                request.max_tokens,
                ResolvedInference.DEFAULT_MAX_TOKENS),

            seed=request.seed,
            stop=request.stop,

            response_schema_json=(
                request.response_schema_json if is_blank(self.contract_schema)
                else self.contract_schema),

            caller_tools=self._without_configured_names(request.caller_tools),

            # Sanitized here, at the boundary, so no broker (built-in or third-party) can ever
            # be handed a passthrough carrying a core-owned key (4.4).
            provider_options_json=ProviderOptions.sanitize(request.provider_options_json).json)

    async def _announce_resolution(self, request: PromptRequest) -> None:
        """Say so in the trace (docs/per-request-inference.md 4.3).

        A rejection the trace does not explain is a turn nobody can account for, and a caller
        whose schema was discarded or whose passthrough key was stripped deserves the same
        courtesy the guardians already extend.
        """
        if not is_blank(self.contract_schema) and not is_blank(request.response_schema_json):
            await self.logging_broker.log_process(
                "Run",
                "Contract → request schema discarded; the configured Contract wins")

        sanitized = ProviderOptions.sanitize(request.provider_options_json)

        if sanitized.malformed:
            await self.logging_broker.log_process(
                "Run", "Provider options → ignored: not a JSON object")

        if sanitized.stripped_keys:
            await self.logging_broker.log_process(
                "Run",
                "Provider options → stripped core-owned key(s): "
                + ", ".join(sanitized.stripped_keys))

        for tool in request.caller_tools:
            if fold(tool.name) in self.configured_tool_names:
                await self.logging_broker.log_process(
                    "Run",
                    f"Caller tools → '{tool.name}' dropped; a configured tool owns that name")

    def _without_configured_names(
            self,
            caller_tools: tuple[ToolDefinition, ...]) -> tuple[ToolDefinition, ...]:
        """A caller tool that shares a configured tool's name is dropped (design 6.1).

        A tool call carrying that name then has exactly one meaning: the configured tool,
        executed locally, under every configured control. Dropped here, before Direction reads
        the list, because a foreign classification downstream would otherwise let a caller
        shadow the deployment's own tool.
        """
        if not caller_tools:
            return caller_tools

        return tuple(
            tool for tool in caller_tools if fold(tool.name) not in self.configured_tool_names)

    def _stopped_because(
            self,
            spend: AgentSpend,
            started_on: datetime,
            cancellation: asyncio.Event | None) -> str | None:
        """Why the run stops at this turn boundary, or None to take the next turn."""
        if cancellation is not None and cancellation.is_set():
            return CANCELLED_MESSAGE

        exhaustion = self._budget_exhaustion(spend, started_on)

        if exhaustion is not None:
            return exhaustion

        if self._is_going_in_circles():
            return self._circles_message

        return None

    def _budget_exhaustion(self, spend: AgentSpend, started_on: datetime) -> str | None:
        if self.budget is None or not self.budget.is_bounded:
            return None

        if self.budget.max_tokens is not None and spend.tokens >= self.budget.max_tokens:
            return TOKEN_BUDGET_MESSAGE

        if (self.budget.max_cost_usd is not None
                and spend.cost_usd(self.budget.cost_per_thousand_tokens)
                >= self.budget.max_cost_usd):

            return COST_BUDGET_MESSAGE

        elapsed = self.time_broker.get_current_date_time() - started_on

        if self.budget.max_wall_clock is not None and elapsed >= self.budget.max_wall_clock:
            return TIME_BUDGET_MESSAGE

        return None

    def _is_going_in_circles(self) -> bool:
        """A run asking for an act the ledger has already answered, again and again.

        Counts replays only: the act that ran, plus each time the ledger answered the same ask
        since, so a read after an edit, which runs, is never counted (SPEC.md 4.10, v1.14).
        """
        run = AgentRun.current()
        replays_of_latest_ask = run.replays_of_latest_ask if run is not None else 0

        return replays_of_latest_ask + 1 >= self.identical_call_limit

    @property
    def _circles_message(self) -> str:
        return circles_message(self.identical_call_limit)

    # Every step of the loop unwinds through one of these: a fault in any step of a run that
    # performed effects unwinds before it surfaces.
    async def _recall_or_unwind(self, context: AgentContext) -> AgentContext:
        try:
            return await self.data_coordination_service.recall(context)
        except Exception:
            await self._unwind()

            raise

    async def _thought_or_unwind(self, context: AgentContext) -> AgentContext:
        try:
            return await self.decision_coordination_service.think(context)
        except Exception:
            await self._unwind()

            raise

    async def _act_or_unwind(self, context: AgentContext) -> AgentContext:
        try:
            return await self.direction_coordination_service.act(context)
        except Exception:
            await self._unwind()

            raise

    async def _unwound_on_fault(
            self,
            decision_stream: DecisionStream) -> AsyncIterator[AgentStreamEvent]:
        """Think's streamed protocol faults inside an enumeration.

        So the enumeration advances inside the unwinding and yields outside it.
        """
        decision_events = aiter(decision_stream)

        async with aclosing(decision_events):
            while True:
                try:
                    decision_event = await anext(decision_events)
                except StopAsyncIteration:
                    return
                except Exception:
                    await self._unwind()

                    raise

                yield decision_event

    async def _screened_or_unwind(
            self,
            context: AgentContext,
            observed_before: int) -> AgentContext:

        # Screening asks Decision for a verdict, and a model call can fail like any other.
        try:
            return await self._screened(context, observed_before)
        except Exception:
            await self._unwind()

            raise

    async def _unwind(self) -> str:
        """Unwind what a run that stopped without an answer left behind (SPEC.md 4.9).

        Compensation asks Direction to unwind the effects, and the caller is told what stood:
        reporting a run cleanly unwound when it was not is worse than never offering
        compensation at all.
        """
        if not self.compensate_on_failure:
            return ""

        outcomes = await self.direction_coordination_service.compensate_run()

        if len(outcomes) == 0:
            return ""

        undone_count = sum(1 for outcome in outcomes if outcome.undone)
        report = f"Unwound {undone_count} of {len(outcomes)} effects."
        standing = [outcome.detail for outcome in outcomes if not outcome.undone]

        await self.logging_broker.log_outcome(f"compensated: {report}")

        return f"{report} {' '.join(standing)}" if standing else report

    async def _voice_narration(self, context: AgentContext, run_events: RunEvents) -> None:
        """The agent says what it is about to do, in the user's language (SPEC.md 6.0).

        Model-authored narration is model output crossing to the user with no Judge and no
        Contract between them: the Gate is its only guardian, so it screens unconditionally
        rather than behind the tool-output flag, which guards model INPUT (SPEC.md 4.9).
        """
        if is_blank(context.narration):
            # The floor: a tool that declared its narration is voiced even when the model said
            # nothing. Host-authored frame on a framework-known slot, so no gate call.
            declared = self.tool_narrations.get(fold(context.direction_type))

            if declared is not None and not is_blank(declared.starting):
                prose = (declared.starting
                         .replace("{tool}", context.direction_type)
                         .replace("{payload}", context.payload))

                await self.logging_broker.log_payload(
                    "Direction", "Narration", prose, detail=True)

                await run_events.write(AgentStreamEvent(AgentStreamEventType.NARRATION, prose))

            return

        verdict = await self.decision_coordination_service.screen(context.narration)

        # Withheld silently, recorded loudly: the user gains nothing from "a progress note was
        # withheld", and echoing the refusal would hand an injected SAY payload a visible
        # oracle, but the record carries the fact (SPEC.md 4.7). The run itself proceeds:
        # narration is decoration, never the work.
        if is_refusal(verdict):
            await self.logging_broker.log_process(
                "Direction", f"Narration → WITHHELD: {verdict}")

            return

        await self.logging_broker.log_payload(
            "Direction", "Narration", context.narration, detail=True)

        await run_events.write(
            AgentStreamEvent(AgentStreamEventType.NARRATION, context.narration))

    async def _voice_observed_narration(
            self,
            context: AgentContext,
            run_events: RunEvents) -> None:
        """The observed slot, voiced immediately before the Tool event that carries the data.

        The narration announces, the Tool event delivers. Never overridden by model narration: a
        SAY line speaks for the act, not for its outcome.
        """
        declared = self.tool_narrations.get(fold(context.direction_type))

        if declared is not None and not is_blank(declared.observed):
            prose = declared.observed.replace("{tool}", context.direction_type)

            await self.logging_broker.log_process(
                "Direction", f"Narration → {prose}", detail=True)

            await run_events.write(AgentStreamEvent(AgentStreamEventType.NARRATION, prose))

    async def _screened(self, acted: AgentContext, observed_before: int) -> AgentContext:
        """A tool's result screened by the Gate before it can become an observation.

        It reuses the Gate rather than adding a guardian, because an instruction arriving inside
        data is the same category of thing as an instruction arriving in a prompt.
        """
        nothing_was_observed = len(acted.observations) <= observed_before

        if not self.screen_tool_output or nothing_was_observed:
            return acted

        verdict = await self.decision_coordination_service.screen(acted.result)

        if not is_refusal(verdict):
            return acted

        refusal = f"the result of '{acted.direction_type}' was refused by screening and withheld"

        await self.logging_broker.log_payload(
            "Direction",
            f"Screening REFUSED the result of '{acted.direction_type}'",
            trim(replace_line_endings(verdict, " ")),
            detail=False)

        return withheld(acted, refusal)

    async def _peek_session(self, session_id: str) -> AgentSession | None:
        """The session as it stood before this run, refused when another principal opened it.

        Read before the run begins, because a resumed run must keep the identity the
        interrupted one had. Nothing is logged here: there is no run yet to credit the record
        to.
        """
        if not session_id:
            return None

        session = await self.data_coordination_service.recall_session(session_id)
        _validate_session_owner(session, self._current_principal())

        return session

    def _current_principal(self) -> str:
        principal = (
            self.principal_resolver.resolve() if self.principal_resolver is not None else None)

        return principal.id if principal is not None and principal.id is not None else ""

    async def _begin_session(self, context: AgentContext) -> None:
        """The start-of-run checkpoint.

        Written before any work, because a crash means nothing at the end runs at all, and an
        identity recorded only on success is an identity the failure case can never use.
        """
        if not context.session_id:
            return

        await self._record_session_with_retry(
            context.session_id,
            lambda existing: checkpoint(context.session_id, existing, _current_run_id()))

    async def _record_session_with_retry(
            self,
            session_id: str,
            compose: Callable[[AgentSession | None], AgentSession]) -> None:
        """Every write is based on a fresh read and says so.

        The version it was read at plus one, and the owner the record already had or the
        principal writing it now. A store that honors versions refuses a write based on a read
        that is no longer current, and the loop reads again and tries again, so no completed
        turn is erased by a slower writer (SPEC.md 4.11).
        """
        for attempt in itertools.count(1):
            existing = await self.data_coordination_service.recall_session(session_id)

            session = dataclasses.replace(
                compose(existing),
                owner=(
                    existing.owner if existing is not None and existing.owner
                    else self._current_principal()),
                version=(existing.version if existing is not None else 0) + 1)

            try:
                await self.data_coordination_service.record_session(session)

                return
            except Exception as exception:
                is_retryable = (
                    is_stale_session_write(exception)
                    and attempt < _MAX_SESSION_WRITE_ATTEMPTS)

                if not is_retryable:
                    raise

                await self.logging_broker.log_process(
                    "Run",
                    f"Session '{session_id}' moved on since it was read; reading it again "
                    f"(attempt {attempt})",
                    detail=True)

    async def _load_session(
            self,
            context: AgentContext,
            session: AgentSession | None) -> AgentContext:

        if session is None:
            return context

        # Bounded, oldest first. An unbounded history makes every prompt in a long conversation
        # cost more than the last, without limit: the bill grows on its own.
        history = session.history

        if len(history) > self.max_history_turns:
            history = history[len(history) - self.max_history_turns:]

        await self.logging_broker.log_process(
            "Data", f"Recalled {len(history)} conversation turn(s)")

        return dataclasses.replace(context, history=history)

    async def _save_session(self, context: AgentContext, is_completed: bool) -> None:
        """Only a completed prompt is recorded.

        A cancelled or budget-stopped run must never be written back as an answer: the next
        prompt would then be told the agent said something it never said.
        """
        if not context.session_id or not is_completed:
            return

        await self._record_session_with_retry(
            context.session_id,
            lambda existing: completed(context, existing, _current_run_id()))


def _first_opinion(configured: _Value | None, requested: _Value | None, default: _Value) -> _Value:
    """The first value anyone expressed: configured, then requested, then the default."""
    if configured is not None:
        return configured

    return requested if requested is not None else default


def _except(names: Sequence[str], removed: Sequence[str]) -> list[str]:
    """Enumerable.Except with OrdinalIgnoreCase: distinct names, first seen first."""
    seen = {fold(name) for name in removed}
    remaining: list[str] = []

    for name in names:
        if fold(name) not in seen:
            seen.add(fold(name))
            remaining.append(name)

    return remaining


def _current_run_id() -> str:
    run = AgentRun.current()

    return run.id if run is not None else ""


def _status_name(status: AgentStatus) -> str:
    """The status as the C# prints it: AWAITING_INPUT is AwaitingInput."""
    return "".join(word.capitalize() for word in status.name.split("_"))


def _validate_prompt(prompt: str | None) -> None:
    if is_blank(prompt):
        raise InvalidAgentException(
            message="Invalid prompt. Please correct the error and try again.")


def _validate_session_owner(session: AgentSession | None, principal: str) -> None:
    """A session belongs to the principal that opened it (SPEC.md 4.11).

    A session with no owner is the anonymous, shared-by-id one that always existed; one with an
    owner admits that owner and no one else.
    """
    if session is not None and session.owner and session.owner != principal:
        raise InvalidAgentException(
            message="Invalid session. It belongs to another principal; use a session of "
                    "your own.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidAgentException as invalid_agent_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_agent_exception)
    except (
            AgentOrchestrationValidationException,
            AgentOrchestrationDependencyValidationException) as validation_exception:

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, _local_exception(validation_exception))
    except (
            AgentOrchestrationDependencyException,
            AgentOrchestrationServiceException) as dependency_exception:

        raise await _create_and_log_dependency_exception(
            logging_broker, _local_exception(dependency_exception))
    except Exception as exception:
        failed_run_management_service_exception = FailedRunManagementServiceException(
            message="Failed agent coordination service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_run_management_service_exception)


async def _mapped_and_logged(logging_broker: LoggingBroker, exception: Exception) -> Exception:
    """The mapping _handling_exceptions applies, on an exception already caught.

    What the streamed door needs, since a generator cannot wrap its yields in the mapping.
    Implemented by raising through the mapping itself, so there is one copy of it and the two
    doors cannot grow different families.
    """
    try:
        async with _handling_exceptions(logging_broker):
            raise exception
    except Exception as mapped_exception:
        return mapped_exception

    return exception


def _local_exception(categorized_exception: Xeption) -> Xeption | None:
    """The local exception a categorized exception wraps, when it is one."""
    inner_exception = categorized_exception.inner_exception

    return inner_exception if isinstance(inner_exception, Xeption) else None


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption | None) -> AgentCoordinationValidationException:

    agent_coordination_validation_exception = AgentCoordinationValidationException(
        message="Agent coordination validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(agent_coordination_validation_exception)

    return agent_coordination_validation_exception


async def _create_and_log_dependency_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption | None) -> AgentCoordinationDependencyValidationException:

    agent_coordination_dependency_validation_exception = (
        AgentCoordinationDependencyValidationException(
            message="Agent coordination dependency validation error occurred, "
                    "fix the error and try again.",
            inner_exception=exception))

    await logging_broker.log_error(agent_coordination_dependency_validation_exception)

    return agent_coordination_dependency_validation_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Xeption | None) -> AgentCoordinationDependencyException:

    agent_coordination_dependency_exception = AgentCoordinationDependencyException(
        message="Agent coordination dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(agent_coordination_dependency_exception)

    return agent_coordination_dependency_exception


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> RunManagementServiceException:

    run_management_service_exception = RunManagementServiceException(
        message="Agent coordination service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(run_management_service_exception)

    return run_management_service_exception
