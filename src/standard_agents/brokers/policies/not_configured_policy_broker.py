# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.policies.policy_broker import PolicyBroker
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision,
)


class NotConfiguredPolicyBroker(PolicyBroker):
    """The default: every registered tool is runnable.

    SPEC.md 4.9: absent every perimeter control, behavior is exactly as if the section did not
    exist, so with no policy configured every registered tool is runnable.
    """

    async def authorize(self, effect: AgentEffect) -> AuthorizationDecision:
        return AuthorizationDecision.allow()
