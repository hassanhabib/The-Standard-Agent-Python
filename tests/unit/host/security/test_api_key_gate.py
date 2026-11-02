# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.host.security import api_key_gate


def test_should_allow_everything_when_no_key_is_configured():
    # given . when
    actual_decision = api_key_gate.allows(
        configured_key=None,
        presented_key=None,
        path="/api/agents/runs")

    # then: an unset key is a deliberate open door, not a locked one with no key cut.
    assert actual_decision is True
