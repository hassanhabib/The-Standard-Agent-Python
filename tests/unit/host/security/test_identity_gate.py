# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# When a deployment configures authentication, an agent route wants an authenticated user and the
# heartbeat stays open; when it configures none, the door is as open as before.

import pytest

from standard_agents.host.security import identity_gate


@pytest.mark.parametrize(
    ("authentication_configured", "user_is_authenticated", "path", "expected_allowed"),
    [
        (False, False, "/api/agents/runs", True),
        (False, False, "/api/V1/agents/runs", True),
        (True, True, "/api/V1/agents/runs", True),
        (True, False, "/api/V1/agents/runs", False),
        (True, False, "/api/agents/streams", False),
        (True, False, "/api/home", True),
        (True, False, "/API/HOME", True),
    ])
def test_should_allow_only_authenticated_users_on_agent_routes_when_authentication_is_configured(
        authentication_configured,
        user_is_authenticated,
        path,
        expected_allowed):

    # when
    actual_allowed = identity_gate.allows(authentication_configured, user_is_authenticated, path)

    # then
    assert actual_allowed is expected_allowed
