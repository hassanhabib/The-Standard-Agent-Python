# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Iterable

from standard_agents.brokers.approvals.approval_broker import ApprovalDecision, ApprovalBroker
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect


class RequireApprovalBroker(ApprovalBroker):
    """The Local mode: a list of tool names that always need someone else to say yes.

    With no approver wired in, the honest answer is PENDING: the act is held, not performed. An
    agent that treated "nobody answered" as consent would be worse than one with no approval at
    all, because the control would read as present while granting everything.
    """

    def __init__(self, tool_names_requiring_approval: Iterable[str]) -> None:
        """Takes the list and keeps nothing of it.

        The list's work happens in composition, where it decides WHICH acts require approval at
        all (DirectionCoordinationService.requires_approval). By the time a request reaches this
        broker the question is always "may this act run?", asked for a listed tool or for an act
        the Ask mode says nothing permitted, and with no approver wired in the honest answer to
        both is the same. Answering APPROVED for a tool absent from the list was consent from
        nobody.
        """

    async def request(self, effect: AgentEffect) -> ApprovalDecision:
        return ApprovalDecision.PENDING
