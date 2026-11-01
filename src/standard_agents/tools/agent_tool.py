# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.agent import Agent
from standard_agents.tools.tool import Tool


_INPUT_PLACEHOLDER = "{input}"


class AgentTool(Tool):
    def __init__(
            self,
            name: str,
            agent: Agent,
            handoff: str = _INPUT_PLACEHOLDER,
            description: str = "",
            parameters: str = "{}") -> None:

        self._name = name
        self._agent = agent
        self._handoff = handoff
        self._description = description
        self._parameters = parameters

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> str:
        return self._parameters

    async def execute(self, input: str) -> str:
        handed_off = self._handoff.replace(_INPUT_PLACEHOLDER, input)
        outcome = await self._agent.run(handed_off, cancellation=None)

        return outcome.result
