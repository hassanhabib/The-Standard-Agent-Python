# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod

from standard_agents.models.orchestrations.agents.agent_context import AgentContext


# Data: what the agent has. Verb: Recall.
class IDataOrchestrationService(ABC):
    @abstractmethod
    async def recall(self, context: AgentContext) -> AgentContext: ...
