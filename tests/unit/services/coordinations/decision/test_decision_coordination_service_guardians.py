# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""SPEC.md 7.6, Invariant 6: a guardian MUST NOT be the Brain.

Guardian output that tries to answer or act is neutralized, treated as a non-authoritative
classification and never executed as the Brain's, and neutralization MUST hold on every path,
since a guardian that can answer on one path is a guardian that can answer.

A Gate is the softest target in the system: it is often the cheapest model, and its output is a
control signal rather than content, so an injected "FINAL: ..." in a gate verdict is a way to
speak straight past the Brain and its Judge.
"""

import dataclasses
from unittest.mock import ANY, call

import pytest

from standard_agents.models.foundations.judges.judgement import Judgement
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


async def test_should_refuse_on_think_if_gate_screens_refuse(
        decision_coordination_service,
        gate_service,
        create_random_agent_context):

    # given
    input_context = create_random_agent_context()
    gate_service.screen.return_value = "refuse"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "Refuse"
    assert actual_context.intent == "Refuse"
