# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from standard_agents.models.brokers.agents.registered_agent import RegisteredAgent


# The fleet seam: where other agents come from (a folder of agent documents, a provider's
# registry, a delegate). Registered agents materialize as tools, so a handoff is an act and the
# perimeter that governs acts governs handoffs.
class IAgentRegistryBroker(ABC):
    @abstractmethod
    async def select_agents(self) -> Sequence[RegisteredAgent]:
        ...
