# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from enum import Enum


# The categories every failure falls into (SPEC.md 3.6, v1.14): the same four The Standard
# sorts every exception into, so a stop reads the same way as a fault.
class AgentFailureCategory(Enum):
    VALIDATION = 0
    DEPENDENCY_VALIDATION = 1
    DEPENDENCY = 2
    SERVICE = 3
