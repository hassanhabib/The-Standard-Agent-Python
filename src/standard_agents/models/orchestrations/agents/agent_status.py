# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from enum import Enum


class AgentStatus(Enum):
    WORKING = 0
    RESPONDED = 1
    AWAITING_INPUT = 2
    REFUSED = 3
    FAILED = 4
    REVISING = 5

    # Terminal for the turn: an effect is proposed but not performed, because an authority has
    # not answered yet (SPEC.md 3.1, 4.9). Distinct from AWAITING_INPUT: the agent is not asking
    # the user a question, it is asking for permission, and waiting is not consent.
    AWAITING_APPROVAL = 6
