# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod

from standard_agents.models.orchestrations.agents.agent_context import AgentContext


# Decision: what the agent thinks. One brain, wrapped in a Gate and a Judge. Verb: Think.
class IDecisionOrchestrationService(ABC):
    @abstractmethod
    async def think(self, context: AgentContext) -> AgentContext: ...
