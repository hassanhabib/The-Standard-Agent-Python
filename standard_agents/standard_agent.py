# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome


class StandardAgent:
    def __init__(self) -> None:
        self.generator_broker = None

    def on_brain(self, generate: Callable[[str, str], Awaitable[str]]) -> "StandardAgent":
        raise NotImplementedError

    async def run(self, prompt: str) -> AgentOutcome:
        raise NotImplementedError
