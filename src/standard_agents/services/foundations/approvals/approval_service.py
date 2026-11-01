# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.approvals.approval_broker import ApprovalBroker, ApprovalDecision
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect


class ApprovalService:
    """Human approval, as a foundation.

    This one matters most of the three. An approval broker reaches a person (a queue, a ticket, a
    chat prompt) and when that is unreachable the honest answer is a dependency failure, never a
    decision. A raw exception escaping into Direction risks being read as "not approved", and a
    system that treats an outage as a verdict is a system that will one day treat it as a yes.
    """

    def __init__(self, *, approval_broker: ApprovalBroker, logging_broker: LoggingBroker) -> None:
        self.approval_broker = approval_broker
        self.logging_broker = logging_broker

    async def request_approval(self, effect: AgentEffect) -> ApprovalDecision:
        """Asks an authority to permit this act. PENDING is not consent (SPEC.md 4.9)."""
        # PENDING must survive the trip untouched. Turning an unanswered request into anything
        # else here is the one mistake that would let silence look like consent.
        return await self.approval_broker.request(effect)
