# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod

from standard_agents.models.orchestrations.agents.agent_context import AgentContext


# Direction: what the agent does. Act internally (a tool), or return to whoever asked. Verb: Act.
class IDirectionOrchestrationService(ABC):
    @abstractmethod
    async def act(self, context: AgentContext) -> AgentContext: ...
