# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome


# The loop. Orchestration is not a fourth nature: it is the composition operator that turns
# Data, Decision and Direction until the run ends.
class IRunCoordinationService(ABC):
    @abstractmethod
    async def run(self, prompt: str) -> AgentOutcome: ...
