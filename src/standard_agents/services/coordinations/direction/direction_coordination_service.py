# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.coordinations.directions.perimeter_policy import PerimeterPolicy
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.effects.compensation_outcome import (
    CompensationOutcome)
from standard_agents.services.orchestrations.direction.executions.execution_orchestration_service \
    import ExecutionOrchestrationService
from standard_agents.services.orchestrations.direction.perimeters.perimeter_orchestration_service \
    import PerimeterOrchestrationService

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
        if _is_terminal(context.direction_type):
            result = await self.execution_service.return_payload(context.payload)

            return dataclasses.replace(
                context,
                result=result,
                status=_to_terminal_status(context.direction_type))

        output = await self.execution_service.run(context.direction_type, context.payload)

        return dataclasses.replace(context, observations=(*context.observations, output))

    async def compensate_run(self) -> tuple[CompensationOutcome, ...]:
        """Unwinds what this run performed, in reverse order (SPEC.md 4.9).

        Reports every effect it could not undo rather than reporting the run cleanly unwound.
        """
        raise NotImplementedError


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
