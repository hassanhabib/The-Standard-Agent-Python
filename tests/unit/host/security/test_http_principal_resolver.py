# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Found in the 2026-09-04 principal review (F-10): the host's API key proved possession of one
# secret and established nobody. Identity now comes from the request's authenticated user, which
# whatever scheme the deployment configured established, and is handed to the agent per act as
# the principal the policy decides on and the audit stamps (SPEC.md 4.9). The wire still has no
# field in which a caller can claim to be someone.

from standard_agents.host.http_context import HttpContext, HttpContextAccessor
from standard_agents.host.security.claims import (
    Claim,
    ClaimsIdentity,
    ClaimsPrincipal,
    ClaimTypes,
)
from standard_agents.host.security.http_principal_resolver import HttpPrincipalResolver
from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal


def _resolver_for(user: ClaimsPrincipal | None) -> HttpPrincipalResolver:
    accessor = HttpContextAccessor()

    if user is not None:
        accessor.http_context = HttpContext(user=user)

    return HttpPrincipalResolver(accessor)


def test_should_resolve_the_authenticated_user_as_the_principal():
    # given: the claims a bearer token carries, in the names the token world uses
    identity = ClaimsIdentity(
        claims=(
            Claim("sub", "hassan"),
            Claim("tid", "peerllm"),
            Claim("jurisdiction", "US-WA"),
            Claim("act", "ops-bot")),
        authentication_type="Bearer")

    resolver = _resolver_for(ClaimsPrincipal(identity))

    expected_principal = AgentPrincipal(
        id="hassan",
        tenant_id="peerllm",
        jurisdiction="US-WA",
        delegated_by="ops-bot")

    # when
    actual_principal = resolver.resolve()

    # then
    assert actual_principal == expected_principal


def test_should_resolve_the_name_identifier_when_there_is_no_subject_claim():
    # given: an identity in the .NET claim vocabulary rather than the token one
    identity = ClaimsIdentity(
        claims=(Claim(ClaimTypes.NAME_IDENTIFIER, "hassan@peerllm.com"),),
        authentication_type="Cookies")

    resolver = _resolver_for(ClaimsPrincipal(identity))
    expected_principal = AgentPrincipal(id="hassan@peerllm.com")

    # when
    actual_principal = resolver.resolve()

    # then
    assert actual_principal == expected_principal
