# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


# How a run ended, as well as what it produced. Only AgentStatus.RESPONDED makes the result an
# answer: a refused, held or exhausted run reads alike as a string.
@dataclass(frozen=True)
class AgentOutcome:
    result: str
    status: AgentStatus
