# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass, field

from standard_agents.models.orchestrations.effects.risk_level import RiskLevel


@dataclass(frozen=True)
class PerformedEffect:
    """An act this run actually performed, and what it produced.

    Recorded so the run can be unwound (SPEC.md 4.9): compensation needs the arguments the tool
    was called with and the outcome it returned, because the outcome carries the identity the
    undo has to name.

    Only performed acts are kept. An effect denied by policy, held for approval, or replayed
    from the ledger was never performed by this run, and compensating it would undo something
    this run did not do.
    """

    tool_name: str
    arguments: str
    outcome: str

    # The act's line in the ledger, so compensating it can be recorded against the same record
    # that says it happened (SPEC.md 4.9). Empty when the act was performed without a ledger.
    idempotency_key: str = field(default="", kw_only=True)

    # What the act touched, as its tool named it, so a later look at the same place can be told
    # from the look before it (SPEC.md 4.9, v1.14). Empty when the tool names nothing.
    scope: str = field(default="", kw_only=True)

    # How consequential the act was. Only an act that is not SAFE changes what a later look at
    # its scope would see.
    risk_level: RiskLevel = field(default=RiskLevel.SAFE, kw_only=True)
