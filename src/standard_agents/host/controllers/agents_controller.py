# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio

from standard_agents.agent import Agent
from standard_agents.host.controllers.action_results import ObjectResult, StreamResult
from standard_agents.host.models.agent_run_request import AgentRunRequest


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
        raise NotImplementedError

    async def post_stream(
            self,
            request: AgentRunRequest,
            *,
            cancellation: asyncio.Event | None = None) -> StreamResult:
        raise NotImplementedError
