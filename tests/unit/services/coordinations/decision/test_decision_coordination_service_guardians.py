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


@pytest.mark.parametrize(
    "verdict",
    ["refuse", "REFUSE", "refuse: asks for credentials", "Refuse - policy violation"])
async def test_should_refuse_on_think_if_gate_screens_refuse_with_reason(
        verdict,
        decision_coordination_service,
        gate_service,
        create_random_agent_context):

    # given
    input_context = create_random_agent_context()
    gate_service.screen.return_value = verdict

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "Refuse"
    assert actual_context.raw_reply == verdict


async def test_should_not_carry_last_turns_narration_on_think_if_gate_refuses(
        decision_coordination_service,
        gate_service,
        create_random_agent_context):
    """Narration is a turn's output, like status and cost.

    The incoming context may still carry the previous turn's, and a refusal path that bypasses
    interpretation would hand it back out: the loop would voice last turn's prose over this
    turn's refusal.
    """
    # given
    input_context = dataclasses.replace(
        create_random_agent_context(),
        narration="stale prose from last turn")

    gate_service.screen.return_value = "refuse"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.narration == ""


async def test_should_not_call_brain_on_think_if_gate_refuses(
        decision_coordination_service,
        gate_service,
        brain_service,
        judge_service,
        create_random_agent_context):

    # given
    input_context = create_random_agent_context()
    gate_service.screen.return_value = "refuse"

    # when
    await decision_coordination_service.think(input_context)

    # then
    assert brain_service.generate.mock_calls == []
    assert judge_service.evaluate.mock_calls == []
    assert brain_service.mock_calls == []
    assert judge_service.mock_calls == []


async def test_should_loop_on_think_if_judge_scores_below_threshold(
        decision_coordination_service,
        brain_service,
        judge_service,
        create_random_agent_context,
        setup_gate_allows):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    brain_service.generate.return_value = "FINAL: a poor answer"
    judge_service.evaluate.return_value = Judgement(score=0.1)

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.status is AgentStatus.REVISING
    assert actual_context.direction_type != "ReturnResponse"


async def test_should_feed_rejected_draft_back_as_observation_on_think(
        decision_coordination_service,
        brain_service,
        judge_service,
        create_random_agent_context,
        setup_gate_allows):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    brain_service.generate.return_value = "FINAL: a poor answer"
    judge_service.evaluate.return_value = Judgement(score=0.1)

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert len(actual_context.observations) == 1
    assert "a poor answer" in actual_context.observations[0]
