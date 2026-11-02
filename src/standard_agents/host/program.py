# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The same agent definition as a service.

Five lines on a laptop, the same five lines behind HTTP: composition here is configuration,
never new concepts, so the appliance guarantee holds at the exposure layer too.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping

from standard_agents.agent import Agent
from standard_agents.host.http_context import HttpContextAccessor
from standard_agents.host.security.claims import ClaimsPrincipal
from standard_agents.host.security.http_principal_resolver import HttpPrincipalResolver
from standard_agents.host.server import AgentHost, HttpRequest

_DEFAULT_URLS = "http://localhost:5000"
_LOGGER = logging.getLogger("standard_agents.host")


def create_host(
        configuration: Mapping[str, str] | None = None,
        *,
        agent_factory: Callable[[HttpPrincipalResolver], Agent] | None = None,
        authenticate: Callable[[HttpRequest], Awaitable[ClaimsPrincipal | None]] | None = None,
) -> AgentHost:
    """The host, composed from configuration as Program.cs composes it.

    configuration holds the keys the C# host reads, named as it names them (Host:ApiKey,
    Agent:Config, urls), compared ignoring case. agent_factory registers the agent: it is
    handed the host's principal resolver and called when the first request needs the agent.
    authenticate is the authentication scheme: it reads a request and returns who it is, or
    None for an anonymous request.
    """
    settings = _Settings(configuration or {})

    # Who is acting comes from the request's authenticated user, translated per act into the
    # principal the policy decides on and the audit stamps (principal review 2026-09-04, F-10).
    # The wire has no field in which a caller can claim to be someone; the scheme establishes
    # them.
    http_context_accessor = HttpContextAccessor()
    principals = HttpPrincipalResolver(http_context_accessor)

    # Naming an issuer (Host:Authentication:Authority) is what configures authentication, and
    # then every agent route wants an authenticated user. Name nothing and the door is as open
    # as before, with no principal handed to the agent.
    authority = settings.get("Host:Authentication:Authority")
    authentication_configured = not _is_blank(authority)

    if authentication_configured and authenticate is None:
        _LOGGER.warning(
            "Host:Authentication:Authority is set, and this host has no scheme that can "
            "validate a bearer token: every agent route answers 401 until create_host is "
            "given an authenticate scheme.")

    return AgentHost(
        lambda: agent_factory(principals),
        urls=_urls(settings),
        api_key=settings.get("Host:ApiKey"),
        authentication_configured=authentication_configured,
        authenticate=authenticate,
        http_context_accessor=http_context_accessor)


class _Settings:
    """Configuration read as ASP.NET reads it: keys compared ignoring case."""

    def __init__(self, configuration: Mapping[str, str]) -> None:
        self._values = {key.upper(): value for key, value in configuration.items()}

    def get(self, key: str) -> str | None:
        return self._values.get(key.upper())


def _is_blank(value: str | None) -> bool:
    return not value or value.isspace()


def _urls(settings: _Settings) -> tuple[str, ...]:
    urls = settings.get("urls") or _DEFAULT_URLS

    return tuple(url.strip() for url in urls.split(";") if url.strip())
