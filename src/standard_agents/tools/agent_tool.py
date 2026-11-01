# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.agent import Agent
from standard_agents.tools.tool import Tool


_INPUT_PLACEHOLDER = "{input}"


class AgentTool(Tool):
    def __init__(self, name: str, agent: Agent, handoff: str = _INPUT_PLACEHOLDER) -> None:
        self._name = name
        self._agent = agent
        self._handoff = handoff

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, input: str) -> str:
        handed_off = self._handoff.replace(_INPUT_PLACEHOLDER, input)
        outcome = await self._agent.run(handed_off, cancellation=None)

        return outcome.result
