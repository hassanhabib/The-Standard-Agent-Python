# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.agent import Agent
from standard_agents.tools.tool import Tool


class AgentTool(Tool):
    def __init__(self, name: str, agent: Agent) -> None:
        self._name = name
        self._agent = agent

    @property
    def name(self) -> str:
        raise NotImplementedError

    async def execute(self, input: str) -> str:
        raise NotImplementedError
