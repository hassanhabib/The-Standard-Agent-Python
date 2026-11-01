# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


async def test_should_return_and_terminate_on_act_if_direction_type_is_return_response(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        return_service,
        create_context_with_direction,
        create_random_string):

    # given
    answer = create_random_string()
    input_context = create_context_with_direction("ReturnResponse", answer)
    return_service.return_payload.return_value = answer

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.result == answer
    assert actual_context.status is AgentStatus.RESPONDED
    assert return_service.mock_calls == [call.return_payload(answer)]
    assert internal_tool_service.mock_calls == []
    assert external_tool_service.mock_calls == []


async def test_should_await_input_and_terminate_on_act_if_direction_type_is_await_input(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        return_service,
        create_context_with_direction,
        create_random_string):

    # given
    question = create_random_string()
    input_context = create_context_with_direction("AwaitInput", question)
    return_service.return_payload.return_value = question

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.result == question
    assert actual_context.status is AgentStatus.AWAITING_INPUT
    assert return_service.mock_calls == [call.return_payload(question)]
    assert internal_tool_service.mock_calls == []
    assert external_tool_service.mock_calls == []


async def test_should_refuse_and_terminate_on_act_if_direction_type_is_refuse(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        return_service,
        create_context_with_direction):

    # given
    refusal = "I'm not able to help with that."
    input_context = create_context_with_direction("Refuse", refusal)
    return_service.return_payload.return_value = refusal

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.result == refusal
    assert actual_context.status is AgentStatus.REFUSED
    assert internal_tool_service.mock_calls == []
    assert external_tool_service.mock_calls == []


async def test_should_run_internal_tool_and_append_observation_on_act(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        create_context_with_direction):

    # given
    input_context = create_context_with_direction("calculator", "1+1")
    internal_tool_service.handles.return_value = True
    internal_tool_service.run.return_value = "2"

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.status is AgentStatus.WORKING
    assert _count_containing(actual_context.observations, "2") == 1
    assert external_tool_service.call.mock_calls == []


async def test_should_route_to_external_and_recover_on_act_if_tool_is_unknown(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        create_context_with_direction):

    # given
    input_context = create_context_with_direction("weather", "today")
    internal_tool_service.handles.return_value = False
    external_tool_service.call.return_value = "[external 'weather' not configured]"

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.status is AgentStatus.WORKING
    assert _count_containing(actual_context.observations, "weather") == 1
    assert external_tool_service.mock_calls == [call.call("weather", "today")]
    assert internal_tool_service.run.mock_calls == []


async def test_should_preserve_existing_observations_on_act(
        direction_coordination_service,
        internal_tool_service,
        create_random_string):

    # given
    prior_observation = create_random_string()

    input_context = AgentContext(
        prompt=create_random_string(),
        direction_type="calculator",
        payload="1+1",
        observations=(prior_observation,))

    internal_tool_service.handles.return_value = True
    internal_tool_service.run.return_value = "2"

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert len(actual_context.observations) == 2
    assert prior_observation in actual_context.observations


def _count_containing(observations: tuple[str, ...], *texts: str) -> int:
    """How many observations contain every text (ContainSingle with a Contains predicate)."""
    return sum(1 for observation in observations if all(text in observation for text in texts))
