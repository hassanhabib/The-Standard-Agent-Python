# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
from enum import Enum
from http import HTTPStatus

from standard_agents.agent import Agent
from standard_agents.host.controllers.action_results import ObjectResult, StreamResult
from standard_agents.host.models.v1.agent_run_request_v1 import AgentRunRequestV1
from standard_agents.host.models.v1.agent_run_response_v1 import AgentRunResponseV1
from standard_agents.host.models.v1.failure_v1 import FailureV1
from standard_agents.host.models.v1.pending_effect_v1 import PendingEffectV1
from standard_agents.host.models.v1.tool_exchange_v1 import ToolExchangeV1
from standard_agents.models.brokers.generators.v1.conversation import ToolDefinition
from standard_agents.models.brokers.sessions.agent_session import AgentTurn
from standard_agents.models.clients.agents.agent_failure import AgentFailure
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect


class AgentsV1Controller:
    """The agent, exposed in full: POST api/V1/agents/runs and api/V1/agents/streams.

    Version 1 of the host's wire contract carries everything a run is (session, transcript,
    caller tools, resumed exchanges, inference controls) and reports everything a run ends with,
    the pending act included. Pure duplex mapping over ONE service dependency (the Agent); the
    prompt-only api/agents routes stay as the convenience door (principal review 2026-09-04,
    F-10).
    """

    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    async def post_run(
            self,
            request: AgentRunRequestV1,
            *,
            cancellation: asyncio.Event | None = None) -> ObjectResult:

        # The caller closing the connection cancels the run at its next turn boundary, and,
        # through the nesting seam, any sub-agents the run started.
        outcome = await self.agent.run(_to_prompt_request(request), cancellation=cancellation)

        return ObjectResult(HTTPStatus.OK, _to_response(outcome))

    async def post_stream(
            self,
            request: AgentRunRequestV1,
            *,
            cancellation: asyncio.Event | None = None) -> StreamResult:
        raise NotImplementedError


def _to_prompt_request(request: AgentRunRequestV1) -> PromptRequest:
    """The wire to the contract, field for field.

    A list the caller leaves out of the document is empty; a field the caller sets to null is
    refused as 400 naming the field before the controller runs, so nothing here has to guess
    what null meant.
    """
    return PromptRequest(
        prompt=request.prompt,
        session_id=request.session_id,

        history=tuple(
            AgentTurn(
                turn.prompt,
                turn.answer,
                exchanges=tuple(_to_tool_exchange(exchange) for exchange in turn.exchanges))
            for turn in request.history),

        tool_exchanges=tuple(_to_tool_exchange(exchange) for exchange in request.tool_exchanges),
        response_schema_json=request.response_schema_json,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        seed=request.seed,
        stop=tuple(request.stop),

        caller_tools=tuple(
            ToolDefinition(tool.name, tool.description, tool.parameters_json)
            for tool in request.caller_tools),

        provider_options_json=request.provider_options_json)


def _to_tool_exchange(exchange: ToolExchangeV1) -> ToolExchange:
    return ToolExchange(
        exchange.call_id,
        exchange.tool_name,
        exchange.arguments_json,
        exchange.result)


def _to_response(outcome: AgentOutcome) -> AgentRunResponseV1:
    return AgentRunResponseV1(
        result=outcome.result,
        status=_enum_name(outcome.status),
        pending_effect=_to_pending_effect(outcome.pending_effect),
        failure=_to_failure(outcome.failure))


def _to_failure(failure: AgentFailure | None) -> FailureV1 | None:
    if failure is None:
        return None

    return FailureV1(
        category=_enum_name(failure.category),
        code=failure.code,
        message=failure.message)


def _to_pending_effect(effect: AgentEffect | None) -> PendingEffectV1 | None:
    if effect is None:
        return None

    return PendingEffectV1(
        run_id=effect.run_id,
        call_id=effect.call_id,
        tool_name=effect.tool_name,
        arguments=effect.arguments,
        scope=effect.scope,
        risk_level=_enum_name(effect.risk_level),
        approval_required=effect.approval_required,
        idempotency_key=effect.idempotency_key,
        principal=effect.principal)


def _enum_name(member: Enum) -> str:
    """The member's C# name, as Enum.ToString() writes it: AwaitingApproval."""
    return "".join(word.capitalize() for word in member.name.split("_"))
