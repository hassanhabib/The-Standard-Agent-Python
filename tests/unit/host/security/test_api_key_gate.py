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


def test_should_allow_the_agent_routes_only_with_the_configured_key():
    # given . when
    matching_decision = api_key_gate.allows(
        configured_key="psk-live-7",
        presented_key="psk-live-7",
        path="/api/agents/runs")

    mismatched_decision = api_key_gate.allows(
        configured_key="psk-live-7",
        presented_key="psk-live-8",
        path="/api/agents/runs")

    absent_decision = api_key_gate.allows(
        configured_key="psk-live-7",
        presented_key=None,
        path="/api/agents/streams")

    # then
    assert matching_decision is True
    assert mismatched_decision is False
    assert absent_decision is False


def test_should_keep_the_heartbeat_open_for_probes():
    # given . when: a load balancer cannot present a key, and the heartbeat tells it nothing an
    # attacker could use.
    actual_decision = api_key_gate.allows(
        configured_key="psk-live-7",
        presented_key=None,
        path="/api/home")

    # then
    assert actual_decision is True
