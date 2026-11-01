# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from enum import Enum


class EffectClaimVerdict(Enum):
    """What the ledger says about an act the run is about to perform (SPEC.md 4.9)."""

    # First time: the claim is this run's, and the act may proceed.
    PROCEED = 0

    # Already performed and recorded: replay the recorded outcome, do not perform.
    REPLAY = 1

    # Another run holds a live claim on it: tell the Brain, do not perform.
    IN_PROGRESS = 2

    # An earlier attempt with no usable outcome (a claim past its lease, a failed tool, a
    # compensation in flight or done). Whether the world changed is unknown, so the run is held
    # with the act as its pending effect until a person reconciles the ledger.
    UNRECONCILED = 3
