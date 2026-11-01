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
