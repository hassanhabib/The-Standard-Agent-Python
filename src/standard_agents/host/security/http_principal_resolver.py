# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.host.http_context import HttpContextAccessor
from standard_agents.host.security.claims import ClaimsPrincipal, ClaimTypes
from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal


class HttpPrincipalResolver:
    """Who is acting, read from the request's authenticated user and handed to the agent per act.

    Whatever scheme the deployment configured established the user; this only translates the
    claims the token world uses into the principal the policy decides on and the audit stamps
    (SPEC.md 4.9). An anonymous request, or no request at all, resolves to nobody: the framework
    consumes a principal and never mints one (principal review 2026-09-04, F-10).
    """

    def __init__(self, http_context_accessor: HttpContextAccessor) -> None:
        self.http_context_accessor = http_context_accessor

    def resolve(self) -> AgentPrincipal | None:
        user = self.http_context_accessor.http_context.user

        # "sub" is the token's subject; NameIdentifier is the same thing in .NET's vocabulary
        # after the default inbound mapping; the identity's name is the last resort.
        principal_id = _first_value(user, "sub", ClaimTypes.NAME_IDENTIFIER)

        if principal_id is None:
            principal_id = user.identity.name

        return AgentPrincipal(
            id=principal_id,
            tenant_id=_first_value(user, "tid", "tenant"),
            jurisdiction=_first_value(user, "jurisdiction"),
            delegated_by=_first_value(user, "act"))


def _first_value(user: ClaimsPrincipal, *claim_types: str) -> str | None:
    """The value of the first of these claim types the user carries, in the order given."""
    for claim_type in claim_types:
        claim = user.find_first(claim_type)

        if claim is not None:
            return claim.value

    return None
