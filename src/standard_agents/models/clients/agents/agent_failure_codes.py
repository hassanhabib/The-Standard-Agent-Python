# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------


# The codes SPEC.md 3.6 (v1.14) names for a run that stopped without an answer. A host may
# report codes of its own for stops these do not name, and must not reuse one of these for a
# different reason.
class AgentFailureCodes:
    # The caller cancelled the run.
    CANCELLED = "cancelled"

    # A token, cost or wall-clock budget ran out.
    BUDGET_EXHAUSTED = "budget_exhausted"

    # The run reached its turn cap still working.
    TURNS_EXHAUSTED = "turns_exhausted"

    # The run kept asking for an act the ledger had already answered.
    GOING_IN_CIRCLES = "going_in_circles"
