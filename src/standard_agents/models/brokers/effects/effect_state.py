# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from enum import Enum


class EffectState(Enum):
    """Where an act stands in the ledger (SPEC.md 4.9).

    The states are typed because the window between "about to run" and "recorded" used to be a
    string, and a process that died inside it left a claim every later proposal read as a
    result (principal review 2026-09-04, F-08).
    """

    # Claimed; the act is running, or a run died before it could say how it ended.
    IN_FLIGHT = 0

    # Performed, and its outcome is on the record; a repeat replays it.
    COMPLETED = 1

    # The tool threw. Whether the world changed is unknown; a repeat is held.
    FAILED = 2

    # Compensation was decided and recorded before it was attempted.
    COMPENSATION_PENDING = 3

    # The act was undone by its compensating act.
    COMPENSATED = 4
