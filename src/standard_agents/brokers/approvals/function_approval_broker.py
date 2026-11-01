# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Awaitable, Callable

from standard_agents.brokers.approvals.approval_broker import ApprovalDecision, ApprovalBroker
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect


class FunctionApprovalBroker(ApprovalBroker):
    """The Custom mode's substrate: a host-supplied approver standing in for a broker.

    A console prompt, an internal service call, a test double.
    """

    def __init__(self, request: Callable[[AgentEffect], Awaitable[ApprovalDecision]]) -> None:
        self._request = request

    async def request(self, effect: AgentEffect) -> ApprovalDecision:
        return await self._request(effect)
