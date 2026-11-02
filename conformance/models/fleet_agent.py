# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class FleetAgent:
    """One scripted specialist in the vector's fleet (SPEC.md 4.8 v1.6).

    The name a handoff calls, the description that advertises it, and a scripted brain of its
    own, so a handoff and a transfer can be certified without a network. rule_gate arms the
    specialist's own deterministic gate, which is how a specialist that REFUSES is scripted: the
    refusal is real, produced by the same control a host would configure.
    """

    REJECTS_UNKNOWN_PROPERTIES: ClassVar[bool] = True

    name: str
    description: str
    replies: list[str]
    rule_gate: list[str] | None = None
