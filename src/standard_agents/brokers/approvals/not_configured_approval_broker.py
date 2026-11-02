# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.approvals.approval_broker import ApprovalDecision, ApprovalBroker
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect


class NotConfiguredApprovalBroker(ApprovalBroker):
    """The default approver: with nobody to ask, every request is PENDING.

    SPEC.md 4.9: absent the control, behavior is exactly as if the section did not exist, and a
    request never reaches this broker unless something explicitly asked for approval.
    requires_approval routes named tools to RequireApprovalBroker at composition, so the only
    path here is PermissionMode.ASK with no approver wired in: a host that said "ask about what
    nothing permitted" and gave nobody to ask. Answering APPROVED there was consent from nobody.
    Waiting is not consent, and an absent authority is nothing but waiting: PENDING.
    """

    async def request(self, effect: AgentEffect) -> ApprovalDecision:
        return ApprovalDecision.PENDING
