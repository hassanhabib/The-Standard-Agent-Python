# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationDecision:
    """Whether an effect may proceed, and why.

    The reason is not optional: a denial without one cannot be audited, cannot be appealed, and
    cannot be told apart from a fault (SPEC.md 4.1).
    """

    permitted: bool
    reason: str

    @classmethod
    def allow(cls) -> AuthorizationDecision:
        return cls(permitted=True, reason="")

    @classmethod
    def deny(cls, reason: str) -> AuthorizationDecision:
        return cls(permitted=False, reason=reason)
