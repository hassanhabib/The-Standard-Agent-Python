# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import pytest

from standard_agents.standard_agent import StandardAgent

# SPEC.md 4.8: every capability is reached three ways, Local (a resource the host already has),
# External (a broker) and Custom (a function), and a mode left out says why. This table is the
# surface; the test makes an undocumented gap fail the build instead of waiting to be noticed.
CAPABILITY_MODES = {
    "skills": {"local": "skills", "external": "use_skills", "custom": "on_skills"},
    "memory": {"local": "memory", "external": "use_memory", "custom": "on_memory"},
    "trace": {"local": "log_to", "external": "use_logging", "custom": "on_log"},
    "brain": {"external": "use_generator", "custom": "on_brain"},
    "knowledge": {"external": "use_knowledge", "custom": "on_knowledge"},
    "gate": {"external": "use_gate", "custom": "on_gate"},
    "judge": {"external": "use_judge", "custom": "on_judge"},
    "remote tools": {"external": "use_mcp", "custom": "on_mcp"},
}

OMITTED_MODES = {
    ("brain", "local"):
        "No model runs without a model runtime, which is a dependency, or an endpoint, which is a "
        + "network; 4.8 forbids Local from requiring either. A local model is an External "
        + "IGeneratorBroker.",
    ("knowledge", "local"):
        "A local folder needs ranked retrieval (4.2), and ranking belongs in a service, not a "
        + "broker; not built in this release.",
    ("gate", "local"):
        "A literal rule that branches on its input is logic, which The Standard keeps out of "
        + "brokers; a rule Gate is one line with on_gate.",
    ("judge", "local"):
        "As for the Gate: a rule Judge is one line with on_judge.",
    ("remote tools", "local"):
        "A built-in client reached by address must speak the protocol's real transports (4.8); "
        + "not built in this release.",
}


@pytest.mark.parametrize("capability", sorted(CAPABILITY_MODES))
def test_should_offer_every_capability_three_ways_or_say_why_not(capability: str) -> None:
    # given
    modes = CAPABILITY_MODES[capability]

    # when
    missing_modes = [
        mode for mode in ("local", "external", "custom")
        if mode not in modes and (capability, mode) not in OMITTED_MODES
    ]

    unbuilt_modes = [
        method_name for method_name in modes.values()
        if not callable(getattr(StandardAgent(), method_name, None))
    ]

    # then
    assert missing_modes == [], f"{capability}: undocumented missing modes {missing_modes}"
    assert unbuilt_modes == [], f"{capability}: modes named but not built {unbuilt_modes}"
