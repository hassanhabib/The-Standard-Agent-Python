# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.brokers.generators.v1.conversation import (
    GenerationResult,
    ModelToolCall)
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.orchestrations.agents.agent_context import AgentContext


async def test_should_think(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows,
        setup_judge_approves):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate.return_value = "FINAL: 42"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "ReturnResponse"
    assert actual_context.payload == "42"
    assert actual_context.raw_reply == "FINAL: 42"


async def test_should_parse_action_from_first_line_only_on_think(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    brain_service.generate.return_value = "ACTION: calculator: 1+1\nFINAL: wrong"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "calculator"
    assert actual_context.payload == "1+1"
    assert "wrong" not in actual_context.payload


async def test_should_preserve_multiline_final_on_think(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows,
        setup_judge_approves):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate.return_value = "FINAL: line one\nline two"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "ReturnResponse"
    assert actual_context.payload == "line one\nline two"
