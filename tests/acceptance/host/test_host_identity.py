# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.host.security.claims import Claim, ClaimsIdentity, ClaimsPrincipal
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


async def _test_authentication(request):
    """A scheme that believes the Authorization header: "Test <subject>" authenticates as that
    subject with a tenant claim.

    It stands in for whatever the deployment configures (bearer tokens from the host's
    configuration, or a proxy's headers), which is exactly the point: the host hands the agent
    whoever the scheme established, and nothing else.
    """
    header = request.headers.get("authorization", "")

    if not header.startswith("Test "):
        return None

    identity = ClaimsIdentity(
        claims=(Claim("sub", header[len("Test "):]), Claim("tid", "peerllm")),
        authentication_type="Test")

    return ClaimsPrincipal(identity)


class _WireTool(Tool):
    @property
    def name(self) -> str:
        return "wire"

    @property
    def description(self) -> str:
        return "Moves money."

    async def execute(self, input: str) -> str:
        return "sent"


async def _wire_brain(system_prompt, user_prompt):
    return "ACTION: wire: 100"


def _authenticated_agent(principals) -> StandardAgent:
    """The real agent behind the door this time, composed the way the host composes it: the
    principal comes from the host's resolver over the request's authenticated user, and an act
    that needs approval is held with that principal on the pending effect."""
    return (
        StandardAgent()
        .without_memory()
        .tool(_WireTool())
        .require_approval("wire")
        .principal(principals.resolve)
        .on_brain(_wire_brain))


async def test_should_hand_the_authenticated_user_to_the_agent_as_the_principal_through_http(
        serve_host,
        v1_document):

    async with serve_host(
            agent_factory=_authenticated_agent,
            authenticate=_test_authentication) as client:

        client.headers["Authorization"] = "Test hassan"

        # when
        response = await client.post_json(
            "api/V1/agents/runs",
            v1_document(prompt="wire the money"))

    actual_response = response.json()

    # then: held for approval, and the act names who asked, as the scheme established it
    assert response.status == 200
    assert actual_response["status"] == "AwaitingApproval"
    assert actual_response["pendingEffect"] is not None
    assert actual_response["pendingEffect"]["principal"] == "hassan"


async def test_should_hand_no_principal_to_the_agent_for_an_anonymous_request_through_http(
        serve_host,
        v1_document):

    # given: the same host, no credential presented, no authentication configured to require one
    async with serve_host(
            agent_factory=_authenticated_agent,
            authenticate=_test_authentication) as client:

        # when
        response = await client.post_json(
            "api/V1/agents/runs",
            v1_document(prompt="wire the money"))

    actual_response = response.json()

    # then: nobody was invented
    assert response.status == 200
    assert actual_response["pendingEffect"]["principal"] is None
