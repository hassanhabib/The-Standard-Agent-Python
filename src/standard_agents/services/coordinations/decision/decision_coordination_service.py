# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator, Callable
from contextlib import aclosing

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.coordinations.decision.decision_stream import DecisionStream
from standard_agents.services.orchestrations.decision.guardians.guardian_orchestration_service \
    import GuardianOrchestrationService
from standard_agents.services.orchestrations.decision.inferences.inference_orchestration_service \
    import InferenceOrchestrationService

_REFUSE_VERDICT = "refuse"
_ROUTE_VERDICT = "route"
_REFUSE_DIRECTION = "Refuse"


class DecisionCoordinationService:
    """The Decision nature: two regions, and the judgment between them.

    Inference asks the model and reads its answer; Guardian screens what goes in and scores what
    comes out. The loop that runs them (screen, resolve a skill conflict, decide, judge, revise)
    belongs to neither, because every step of it depends on the other region's result.
    """

    def __init__(
            self,
            *,
            inference_service: InferenceOrchestrationService,
            guardian_service: GuardianOrchestrationService,
            logging_broker: LoggingBroker,
            contract_schema: str | None = None) -> None:

        self.inference_service = inference_service
        self.guardian_service = guardian_service
        self.logging_broker = logging_broker

        # The shape every answer is held to, or empty. Configuration rather than a collaborator:
        # it is a string the host chose, and the foundation treats an empty one as no check.
        self.contract_schema = contract_schema if contract_schema is not None else ""

    async def screen(self, text: str) -> str:
        raise NotImplementedError

    async def think(self, context: AgentContext) -> AgentContext:
        verdict = await self.guardian_service.screen(context.prompt)
        context = await self._routed_by_gate(context, verdict)

        return await self.inference_service.decide(context)

    def think_stream(self, context: AgentContext) -> DecisionStream:
        """The streamed door.

        Draft segments are yielded as they arrive; the decided context is the stream's result
        once the enumeration completes.
        """
        return DecisionStream(
            lambda set_result: self._stream_think(context, set_result))

    async def _stream_think(
            self,
            context: AgentContext,
            set_result: Callable[[AgentContext], None]) -> AsyncIterator[AgentStreamEvent]:

        verdict = await self.guardian_service.screen(context.prompt)
        refused = await self._refused_by_gate(context, verdict)

        if refused is not None:
            set_result(refused)

            yield AgentStreamEvent(AgentStreamEventType.STATUS, "gate refused the request")

            return

        context = await self._routed_by_gate(context, verdict)
        decided = context

        def set_decided(interpreted: AgentContext) -> None:
            nonlocal decided
            decided = interpreted

        drafting = self.inference_service.decide_stream(context, set_decided)

        async with aclosing(drafting):
            async for segment in drafting:
                yield segment

        set_result(decided)

    async def _refused_by_gate(self, context: AgentContext, verdict: str) -> AgentContext | None:
        """The Gate's refusal, handled once for both doors, or None when the Gate did not refuse."""
        if not _is_refusal(verdict):
            return None

        return dataclasses.replace(context, direction_type=_REFUSE_DIRECTION)

    async def _routed_by_gate(self, context: AgentContext, verdict: str) -> AgentContext:
        """Everything else the Gate's verdict carries, handled once for both doors.

        A route label rides through as data.
        """
        return (
            dataclasses.replace(context, route=_extract_route_label(verdict))
            if _is_route(verdict)
            else context)


def _is_refusal(verdict: str) -> bool:
    return verdict.startswith(_REFUSE_VERDICT)


def _is_route(verdict: str) -> bool:
    return verdict.startswith(_ROUTE_VERDICT)


def _extract_route_label(verdict: str) -> str:
    return verdict[len(_ROUTE_VERDICT):].lstrip(": ")
