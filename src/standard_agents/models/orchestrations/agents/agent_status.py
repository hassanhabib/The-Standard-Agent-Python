# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from enum import Enum


# The closed set of SPEC.md 3.1. WORKING is the default; the loop continues while a run is
# WORKING and stops on anything else. AWAITING_APPROVAL means an act was proposed and is held for
# an authority, which is not the same as AWAITING_INPUT, where the agent asked the user.
class AgentStatus(Enum):
    WORKING = 0
    RESPONDED = 1
    AWAITING_INPUT = 2
    AWAITING_APPROVAL = 3
    REFUSED = 4
    FAILED = 5
