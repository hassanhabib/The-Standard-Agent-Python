# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


# Whether an effect may proceed, and why. The reason is not optional: a denial without one
# cannot be audited, cannot be appealed, and cannot be told apart from a fault (SPEC.md 4.1).
@dataclass(frozen=True)
class AuthorizationDecision:
    permitted: bool
    reason: str

    @staticmethod
    def allow() -> "AuthorizationDecision":
        return AuthorizationDecision(permitted=True, reason="")

    @staticmethod
    def deny(reason: str) -> "AuthorizationDecision":
        return AuthorizationDecision(permitted=False, reason=reason)
