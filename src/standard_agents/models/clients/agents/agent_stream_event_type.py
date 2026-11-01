# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from enum import Enum


class AgentStreamEventType(Enum):
    STATUS = 0
    THINKING = 1
    TOOL = 2
    RESPONSE = 3

    # User-voiced progress prose ("Let me check the web..."), screened before it is emitted.
    # Distinct from STATUS, which is machine-voiced, and from THINKING, which is unvetted draft.
    NARRATION = 4

    # What the run has spent so far, after every model call (SPEC.md 4.14.1): a running total
    # carried whole on the event's usage, and as a number in its content. Never an answer.
    USAGE = 5
