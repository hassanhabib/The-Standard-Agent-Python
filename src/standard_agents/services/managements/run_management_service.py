# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable, Mapping

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.telemetries.not_configured_telemetry_broker import (
    NotConfiguredTelemetryBroker)
from standard_agents.brokers.telemetries.telemetry_broker import TelemetryBroker
from standard_agents.brokers.times.system_time_broker import SystemTimeBroker
from standard_agents.brokers.times.time_broker import TimeBroker
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_run_stream import AgentRunStream
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.coordinations.agents.agent_budget import AgentBudget
from standard_agents.models.coordinations.agents.principal_resolver import PrincipalResolver
from standard_agents.models.coordinations.agents.tool_narration import ToolNarration
from standard_agents.models.coordinations.agents.tool_selector import ToolSelector
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.coordinations.data.data_coordination_service import (
    DataCoordinationService)
from standard_agents.services.coordinations.decision.decision_coordination_service import (
    DecisionCoordinationService)
from standard_agents.services.coordinations.direction.direction_coordination_service import (
    DirectionCoordinationService)

_DEFAULT_MAX_TURNS = 7

# Above the default turn cap, so a composition that never set it is bounded by the turn cap
# exactly as before (SPEC.md 4.10, v1.14).
_DEFAULT_IDENTICAL_CALL_LIMIT = 8

_DEFAULT_KNOWLEDGE_CITATION_PREFIX = "Source: "


class RunManagementService:
    """The run: Data, Decision and Direction, turn after turn, until the agent has an answer.

    One loop, read through four doors: the answer (process_prompt), how the run ended (run),
    the run's events as they happen (process_prompt_stream), and both at once (run_stream).
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
        self.configured_tool_names = tuple(configured_tool_names or ())

        # What the tools declared they say, keyed by tool name: derived data, like risk and
        # scope, so the loop can voice acts without holding the tools.
        self.tool_narrations = dict(tool_narrations or {})

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
        """The run's answer, or the reason there is not one."""
        outcome = await self._run(
            PromptRequest(prompt=prompt, session_id=session_id),
            cancellation)

        return outcome.result

    async def run(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AgentOutcome:
        """The run asked for by a request, reported with how it ended."""
        raise NotImplementedError

    def process_prompt_stream(
            self,
            prompt: str,
            *,
            session_id: str = "",
            cancellation: asyncio.Event | None = None) -> AsyncIterator[AgentStreamEvent]:
        """The run's events as they happen."""
        raise NotImplementedError

    def run_stream(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AgentRunStream:
        """The run's events as they happen, and how it ended once they are read."""
        raise NotImplementedError

    async def _run(
            self,
            request: PromptRequest,
            cancellation: asyncio.Event | None) -> AgentOutcome:

        context = AgentContext(prompt=request.prompt)
        context = await self.data_coordination_service.recall(context)
        context = await self.direction_coordination_service.act(context)

        return AgentOutcome(context.result, context.status)
