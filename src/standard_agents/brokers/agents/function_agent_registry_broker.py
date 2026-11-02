# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from standard_agents.brokers.agents.agent_registry_broker import AgentRegistryBroker
from standard_agents.models.brokers.agents.registered_agent import RegisteredAgent


class FunctionAgentRegistryBroker(AgentRegistryBroker):
    """The Custom mode of the fleet seam: your own code decides which agents exist.

    Asked per selection: a database of tenants' agents, a feature flag, a directory service.
    """

    def __init__(self, select: Callable[[], Awaitable[Sequence[RegisteredAgent]]]) -> None:
        self._select = select

    async def select_agents(self) -> Sequence[RegisteredAgent]:
        return await self._select()
