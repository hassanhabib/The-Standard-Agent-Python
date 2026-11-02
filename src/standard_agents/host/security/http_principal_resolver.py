# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.host.http_context import HttpContextAccessor
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
        raise NotImplementedError
