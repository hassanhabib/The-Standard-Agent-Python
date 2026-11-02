# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingEffectV1:
    """The act the run is waiting on.

    A caller's tool call to execute and answer, or an act held for an authority's decision. The
    call id is the model's own, so the caller can answer it; the idempotency key identifies the
    act, so a decision names exactly one act.
    """

    run_id: str
    call_id: str
    tool_name: str
    arguments: str
    scope: str
    risk_level: str
    approval_required: bool
    idempotency_key: str
    principal: str | None
