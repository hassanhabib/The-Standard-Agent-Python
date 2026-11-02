# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The same agent definition as a service.

Five lines on a laptop, the same five lines behind HTTP: composition here is configuration,
never new concepts, so the appliance guarantee holds at the exposure layer too.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping

from standard_agents.agent import Agent
from standard_agents.host.security.claims import ClaimsPrincipal
from standard_agents.host.security.http_principal_resolver import HttpPrincipalResolver
from standard_agents.host.server import AgentHost, HttpRequest


def create_host(
        configuration: Mapping[str, str] | None = None,
        *,
        agent_factory: Callable[[HttpPrincipalResolver], Agent] | None = None,
        authenticate: Callable[[HttpRequest], Awaitable[ClaimsPrincipal | None]] | None = None,
) -> AgentHost:

    raise NotImplementedError
