# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from enum import Enum


class AuditKind(Enum):
    RUN = 0
    TURN = 1
    STEP = 2
    PROCESS = 3
    OUTCOME = 4
    ERROR = 5
