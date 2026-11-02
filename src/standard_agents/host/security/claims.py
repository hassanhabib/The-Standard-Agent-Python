# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Who a request is, as an authentication scheme established it.

The shapes ASP.NET hands a host (System.Security.Claims), kept to what the host reads: a
scheme authenticates a request into a principal, the identity gate asks whether it is
authenticated, and the principal resolver translates its claims into an AgentPrincipal.
"""

from __future__ import annotations

from dataclasses import dataclass


class ClaimTypes:
    """The claim types .NET names in its own vocabulary, beside the token world's "sub"."""

    NAME = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
    NAME_IDENTIFIER = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier"


@dataclass(frozen=True)
class Claim:
    type: str
    value: str


@dataclass(frozen=True)
class ClaimsIdentity:
    """One identity: its claims, and the scheme that authenticated it, if any did."""

    claims: tuple[Claim, ...] = ()
    authentication_type: str | None = None

    @property
    def is_authenticated(self) -> bool:
        """Whether a scheme vouched for this identity; an anonymous one names no scheme."""
        return bool(self.authentication_type)

    @property
    def name(self) -> str | None:
        claim = self.find_first(ClaimTypes.NAME)

        return claim.value if claim is not None else None

    def find_first(self, claim_type: str) -> Claim | None:
        """The first claim of a type, the type compared ignoring case, as .NET compares it."""
        for claim in self.claims:
            if claim.type.upper() == claim_type.upper():
                return claim

        return None


@dataclass(frozen=True)
class ClaimsPrincipal:
    """The request's user. An anonymous request is a principal whose identity is anonymous."""

    identity: ClaimsIdentity | None = ClaimsIdentity()

    def find_first(self, claim_type: str) -> Claim | None:
        if self.identity is None:
            return None

        return self.identity.find_first(claim_type)
