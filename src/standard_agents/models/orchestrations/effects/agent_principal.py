# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPrincipal:
    """Who is acting, in the terms a policy actually decides on (SPEC.md 4.9).

    Every field beyond id is optional. A host that has only a user id supplies only that, and
    nothing about the perimeter changes. The framework consumes a principal, it does not mint
    one: establishing identity (tokens, sessions, sign-in) is the host's.
    """

    # Who is acting. The one field an identity cannot be without.
    id: str = ""

    # Which tenant they belong to, where one agent serves several.
    tenant_id: str | None = None

    # Which legal or regulatory regime this act falls under.
    jurisdiction: str | None = None

    # Who this principal is acting for, when the act is delegated.
    delegated_by: str | None = None

    def __str__(self) -> str:
        """Reads as the identifier, so a trace or a message says who without ceremony."""
        return self.id
