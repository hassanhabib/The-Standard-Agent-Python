# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.policies.policy_broker import PolicyBroker
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision)


class PolicyService:
    """Authorization, as a foundation rather than as a broker reached from Direction.

    A policy engine is usually somewhere else: a rules service, an OPA sidecar, a database. When
    it is unreachable, that has to arrive as a POLICY failure. Reached directly from Direction it
    arrived as an unmapped HttpRequestException blamed on the orchestration, which is a trace that
    sends someone to read the wrong code (docs/architecture-alignment.md).
    """

    def __init__(self, *, policy_broker: PolicyBroker, logging_broker: LoggingBroker) -> None:
        self.policy_broker = policy_broker
        self.logging_broker = logging_broker

    async def authorize_effect(self, effect: AgentEffect) -> AuthorizationDecision:
        """May this act happen, and if not, why not (SPEC.md 4.9)?"""
        raise NotImplementedError
