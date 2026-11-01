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


async def test_should_preserve_colons_in_tool_input_on_think(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    brain_service.generate.return_value = "ACTION: fetch: https://example.com:8080/a?b=1"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "fetch"
    assert actual_context.payload == "https://example.com:8080/a?b=1"


async def test_should_set_intent_to_tool_name_on_think_if_action(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    brain_service.generate.return_value = "ACTION: calculator: 1+1"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.intent == "calculator"


async def test_should_set_intent_to_respond_on_think_if_final(
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
    assert actual_context.intent == "Respond"


async def test_should_treat_non_protocol_reply_as_answer_on_think(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows,
        setup_judge_approves):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate.return_value = "just an answer, no prefix"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "ReturnResponse"
    assert actual_context.payload == "just an answer, no prefix"


@pytest.mark.parametrize("reply", ["ACTION:", "ACTION: ", "ACTION: : missing tool name"])
async def test_should_treat_empty_action_as_answer_on_think(
        reply,
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows,
        setup_judge_approves):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate.return_value = reply

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "ReturnResponse"
    assert actual_context.intent == "Respond"


async def test_should_pass_observations_to_brain_on_think(
        decision_coordination_service,
        brain_service,
        create_random_string,
        setup_gate_allows,
        setup_judge_approves,
        containing):

    # given
    observation = create_random_string()

    input_context = AgentContext(
        prompt=create_random_string(),
        system_prompt=create_random_string(),
        observations=(observation,))

    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate.return_value = "FINAL: done"

    # when
    await decision_coordination_service.think(input_context)

    # then
    expected_generate_call = call(
        system_prompt=input_context.system_prompt,
        user_prompt=containing(observation))

    assert brain_service.generate.mock_calls.count(expected_generate_call) == 1
