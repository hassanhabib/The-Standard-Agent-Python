# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable

from standard_agents.brokers.policies.policy_broker import PolicyBroker
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision,
)


class FunctionPolicyBroker(PolicyBroker):
    """The Custom mode's substrate: a host-supplied function standing in for a broker."""

    def __init__(
            self,
            authorize: Callable[[AgentEffect], Awaitable[AuthorizationDecision]]) -> None:

        self._authorize = authorize

    async def authorize(self, effect: AgentEffect) -> AuthorizationDecision:
        return await self._authorize(effect)
