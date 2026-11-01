# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect


class ApprovalDecision(Enum):
    # Proceed: the act was authorized by a human or a trusted authority.
    APPROVED = 0

    # Do not proceed. Non-terminal: the agent may choose another path.
    DENIED = 1

    # No answer yet. The turn stops with AwaitingApproval and the act does not run: waiting is
    # not consent (SPEC.md 4.9).
    PENDING = 2


class ApprovalBroker(ABC):
    @abstractmethod
    async def request(self, effect: AgentEffect) -> ApprovalDecision:
        ...
