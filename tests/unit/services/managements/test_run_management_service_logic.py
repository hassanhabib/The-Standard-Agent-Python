# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses
from unittest.mock import ANY, Mock, call

from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


async def test_should_process_prompt(
        run_management_service,
        create_random_string,
        setup_orchestrations_pass_through,
        setup_direction_terminates):

    # given
    random_prompt = create_random_string()
    expected_result = create_random_string()

    setup_orchestrations_pass_through()
    setup_direction_terminates(expected_result)

    # when
    actual_result = await run_management_service.process_prompt(random_prompt)

    # then
    assert actual_result == expected_result


async def test_should_seed_context_with_prompt_on_process_prompt(
        run_management_service,
        data_coordination_service,
        create_random_string,
        setup_orchestrations_pass_through,
        setup_direction_terminates):

    # given
    random_prompt = create_random_string()

    setup_orchestrations_pass_through()
    setup_direction_terminates(create_random_string())

    # when
    await run_management_service.process_prompt(random_prompt)

    # then
    [recall_call] = data_coordination_service.recall.mock_calls
    recalled_context = recall_call.args[0]

    assert recalled_context.prompt == random_prompt
    assert recalled_context.status is AgentStatus.WORKING


async def test_should_call_recall_think_act_in_order_on_process_prompt(
        run_management_service,
        data_coordination_service,
        decision_coordination_service,
        direction_coordination_service,
        create_random_string):

    # given
    random_prompt = create_random_string()
    sequence = Mock()
    sequence.attach_mock(data_coordination_service.recall, "recall")
    sequence.attach_mock(decision_coordination_service.think, "think")
    sequence.attach_mock(direction_coordination_service.act, "act")

    data_coordination_service.recall.side_effect = lambda context: context
    decision_coordination_service.think.side_effect = lambda context: context

    direction_coordination_service.act.side_effect = lambda context: dataclasses.replace(
        context, result="done", status=AgentStatus.RESPONDED)

    # when
    actual_result = await run_management_service.process_prompt(random_prompt)

    # then
    assert actual_result == "done"
    assert sequence.mock_calls == [call.recall(ANY), call.think(ANY), call.act(ANY)]
