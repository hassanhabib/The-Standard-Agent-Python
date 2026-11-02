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
from standard_agents.host.controllers.server_sent_events import to_server_sent_events
from standard_agents.host.models.agent_run_request import AgentRunRequest
from standard_agents.host.models.agent_run_response import AgentRunResponse


class AgentsController:
    """The agent, exposed: POST api/agents/runs and api/agents/streams.

    Pure duplex mapping over ONE service dependency (the Agent): no business logic lives here,
    because an exposer is disposable and the loop is not.
    """

    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    async def post_run(
            self,
            request: AgentRunRequest,
            *,
            cancellation: asyncio.Event | None = None) -> ObjectResult:

        if _is_blank(request.prompt):
            return ObjectResult(HTTPStatus.BAD_REQUEST, "prompt is required")

        # The caller closing the connection cancels the run at its next turn boundary, and,
        # through the nesting seam, any sub-agents the run started.
        outcome = await self.agent.run(request.prompt, cancellation=cancellation)

        return ObjectResult(
            HTTPStatus.OK,
            AgentRunResponse(result=outcome.result, status=_enum_name(outcome.status)))

    async def post_stream(
            self,
            request: AgentRunRequest,
            *,
            cancellation: asyncio.Event | None = None) -> StreamResult:
        """The streamed door, as server-sent events."""

        if _is_blank(request.prompt):
            return StreamResult(HTTPStatus.BAD_REQUEST)

        stream_events = self.agent.process_prompt_stream(request.prompt, cancellation=cancellation)

        return StreamResult(
            HTTPStatus.OK,
            "text/event-stream",
            to_server_sent_events(stream_events))


def _is_blank(prompt: str | None) -> bool:
    return not prompt or prompt.isspace()


def _enum_name(member: Enum) -> str:
    """The member's C# name, as Enum.ToString() writes it: AwaitingApproval."""
    return "".join(word.capitalize() for word in member.name.split("_"))
