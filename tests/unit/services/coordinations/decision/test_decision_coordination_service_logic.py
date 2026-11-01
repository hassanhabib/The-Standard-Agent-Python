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


async def test_should_route_structured_tool_call_on_think(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()

    brain_service.generate.return_value = (
        'TOOL: {"tool":"calculator","arguments":{"expression":"47*89"}}')

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "calculator"
    assert actual_context.intent == "calculator"
    assert "47*89" in actual_context.payload


async def test_should_treat_malformed_tool_call_as_answer_on_think(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows,
        setup_judge_approves):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate.return_value = "TOOL: this is not valid json"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "ReturnResponse"


async def test_should_peel_narration_before_interpreting_on_think(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    brain_service.generate.return_value = "SAY: Checking the numbers...\nACTION: calculator: 2+2"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "calculator"
    assert actual_context.payload == "2+2"
    assert actual_context.narration == "Checking the numbers..."


async def test_should_peel_only_the_first_say_line_on_think(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows,
        setup_judge_approves):
    """At most one SAY per turn (SPEC.md 6.0): only the first leading line is narration.

    A second one is not: it is part of the reply, exactly as a non-supporting implementation
    would have read it.
    """
    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate.return_value = "SAY: one\nSAY: two\nACTION: calculator: 2+2"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.narration == "one"
    assert actual_context.direction_type == "ReturnResponse"
    assert "SAY: two" in actual_context.payload


async def test_should_carry_native_narration_on_think(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    brain_service.speaks_natively = True

    brain_service.generate_natively.return_value = GenerationResult(
        narration="Let me check...",
        tool_calls=(ModelToolCall("call_1", "calculator", "{}"),))

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "calculator"
    assert actual_context.narration == "Let me check..."


async def test_should_return_empty_answer_without_judging_on_think(
        decision_coordination_service,
        brain_service,
        judge_service,
        create_random_agent_context,
        setup_gate_allows):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    brain_service.generate.return_value = "FINAL:"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "ReturnResponse"
    assert actual_context.payload == ""
    assert judge_service.evaluate.mock_calls == []


async def test_should_stream_answer_draft_as_thinking_on_think_stream(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows,
        setup_judge_approves,
        to_async_stream,
        drain):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate_stream.return_value = to_async_stream("Hello ", "there!")

    # when
    decision_stream = decision_coordination_service.think_stream(input_context)
    actual_events = await drain(decision_stream)

    # then
    assert not any(
        stream_event.type is AgentStreamEventType.RESPONSE for stream_event in actual_events)

    streamed_draft = "".join(
        stream_event.content
        for stream_event in actual_events
        if stream_event.type is AgentStreamEventType.THINKING)

    assert streamed_draft == "Hello there!"
    assert decision_stream.result.direction_type == "ReturnResponse"
    assert decision_stream.result.payload == "Hello there!"


async def test_should_stream_tool_reasoning_as_thinking_on_think_stream(
        decision_coordination_service,
        brain_service,
        judge_service,
        create_random_agent_context,
        setup_gate_allows,
        to_async_stream,
        drain):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    brain_service.generate_stream.return_value = to_async_stream("ACTION: cal", "culator: 2+2")

    # when
    decision_stream = decision_coordination_service.think_stream(input_context)
    actual_events = await drain(decision_stream)

    # then
    assert any(
        stream_event.type is AgentStreamEventType.THINKING for stream_event in actual_events)

    assert not any(
        stream_event.type is AgentStreamEventType.RESPONSE for stream_event in actual_events)

    assert decision_stream.result.direction_type == "calculator"
    assert decision_stream.result.payload == "2+2"
    assert judge_service.evaluate.mock_calls == []


async def test_should_stream_final_draft_as_thinking_on_think_stream(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows,
        setup_judge_approves,
        to_async_stream,
        drain):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate_stream.return_value = to_async_stream("FINAL: ", "The answer is 42.")

    # when
    decision_stream = decision_coordination_service.think_stream(input_context)
    actual_events = await drain(decision_stream)

    # then
    assert any(
        stream_event.type is AgentStreamEventType.THINKING for stream_event in actual_events)

    assert not any(
        stream_event.type is AgentStreamEventType.RESPONSE for stream_event in actual_events)

    assert decision_stream.result.payload == "The answer is 42."


async def test_should_swallow_say_line_from_thinking_stream_on_think_stream(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows,
        to_async_stream,
        drain):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()

    # "SAY: Chec" is nine characters, exactly the length at which the classifier commits a
    # channel today, so the narration line must be recognized before that commit.
    brain_service.generate_stream.return_value = to_async_stream(
        "SAY: Chec", "king...\nACTION: calculator: 2+2")

    # when
    decision_stream = decision_coordination_service.think_stream(input_context)
    actual_events = await drain(decision_stream)

    # then
    assert not any(
        "Checking" in stream_event.content or "SAY:" in stream_event.content
        for stream_event in actual_events)

    assert decision_stream.result.direction_type == "calculator"
    assert decision_stream.result.payload == "2+2"
    assert decision_stream.result.narration == "Checking..."


async def test_should_swallow_unterminated_say_line_on_think_stream_flush(
        decision_coordination_service,
        brain_service,
        create_random_agent_context,
        setup_gate_allows,
        to_async_stream,
        drain):
    """The stream can end mid-narration: a SAY line with no newline ever.

    The prose is still swallowed, never leaked as thinking, and still reaches the loop on the
    context, while the empty remainder closes the turn through the empty-answer path.
    """
    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    brain_service.generate_stream.return_value = to_async_stream("SAY: Work", "ing on it")

    # when
    decision_stream = decision_coordination_service.think_stream(input_context)
    actual_events = await drain(decision_stream)

    # then
    assert not any(
        "Working on it" in stream_event.content or "SAY:" in stream_event.content
        for stream_event in actual_events)

    assert decision_stream.result.narration == "Working on it"
    assert decision_stream.result.direction_type == "ReturnResponse"
    assert decision_stream.result.payload == ""


async def test_should_not_stream_response_on_think_stream_if_gate_refuses(
        decision_coordination_service,
        gate_service,
        brain_service,
        create_random_agent_context,
        drain):

    # given
    input_context = create_random_agent_context()
    gate_service.screen.return_value = "refuse: policy"

    # when
    decision_stream = decision_coordination_service.think_stream(input_context)
    actual_events = await drain(decision_stream)

    # then
    assert any(
        stream_event.type is AgentStreamEventType.STATUS
        and stream_event.content == "gate refused the request"
        for stream_event in actual_events)

    assert not any(
        stream_event.type is AgentStreamEventType.RESPONSE for stream_event in actual_events)

    assert decision_stream.result.direction_type == "Refuse"
    assert brain_service.generate_stream.mock_calls == []


async def test_should_capture_gate_route_label_as_data_on_think(
        decision_coordination_service,
        gate_service,
        brain_service,
        create_random_agent_context,
        setup_judge_approves):
    """Found in the 2026-08-23 sweep: the route label was captured on the streamed door only.

    The mirror image of every other asymmetry, and the same defect. Data consumes context.route
    on both paths (retrieve_instructions), so a Gate that answered "route: X" steered skill
    selection when the caller streamed and was silently ignored when the caller did not.
    """
    # given: the identical verdict the streamed test uses
    input_context = create_random_agent_context()
    setup_judge_approves()
    gate_service.screen.return_value = "route: arithmetic"
    brain_service.generate.return_value = "FINAL: 42"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then: the label rides through as data on this door too
    assert actual_context.route == "arithmetic"
