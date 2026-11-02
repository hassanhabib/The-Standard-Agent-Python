# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio

from standard_agents.agent import Agent
from standard_agents.host.controllers.action_results import ObjectResult, StreamResult
from standard_agents.host.models.v1.agent_run_request_v1 import AgentRunRequestV1


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
        raise NotImplementedError

    async def post_stream(
            self,
            request: AgentRunRequestV1,
            *,
            cancellation: asyncio.Event | None = None) -> StreamResult:
        raise NotImplementedError
