# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses
from unittest.mock import ANY, Mock, call

import pytest

from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.services.managements.run_management_service import RunManagementService


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


@pytest.mark.parametrize("terminal_status", [
    AgentStatus.RESPONDED,
    AgentStatus.REFUSED,
    AgentStatus.FAILED,
    AgentStatus.AWAITING_INPUT])
async def test_should_break_loop_on_process_prompt_if_status_is_not_working(
        terminal_status,
        run_management_service,
        data_coordination_service,
        direction_coordination_service,
        create_random_string,
        setup_orchestrations_pass_through):

    # given
    random_prompt = create_random_string()
    setup_orchestrations_pass_through()

    direction_coordination_service.act.side_effect = lambda context: dataclasses.replace(
        context, result="stopped", status=terminal_status)

    # when
    actual_result = await run_management_service.process_prompt(random_prompt)

    # then
    assert actual_result == "stopped"
    assert data_coordination_service.recall.mock_calls == [call(ANY)]


async def test_should_cap_turns_on_process_prompt_if_brain_never_terminates(
        run_management_service,
        data_coordination_service,
        decision_coordination_service,
        create_random_string,
        setup_orchestrations_pass_through,
        setup_direction_never_terminates):

    # given
    random_prompt = create_random_string()
    setup_orchestrations_pass_through()
    setup_direction_never_terminates("again")

    # when
    actual_result = await run_management_service.process_prompt(random_prompt)

    # then: the capped run delivered no answer, and says so rather than handing back the last
    # tool output as though it were one.
    assert "out of turns" in actual_result
    assert "again" not in actual_result
    assert data_coordination_service.recall.mock_calls == [call(ANY)] * 7
    assert decision_coordination_service.think.mock_calls == [call(ANY)] * 7


async def test_should_cap_turns_at_configured_maximum_on_process_prompt(
        data_coordination_service,
        decision_coordination_service,
        direction_coordination_service,
        logging_broker,
        create_random_string,
        setup_orchestrations_pass_through,
        setup_direction_never_terminates):

    # given
    random_prompt = create_random_string()
    configured_max_turns = 3

    bounded_run_management_service = RunManagementService(
        data_coordination_service=data_coordination_service,
        decision_coordination_service=decision_coordination_service,
        direction_coordination_service=direction_coordination_service,
        logging_broker=logging_broker,
        max_turns=configured_max_turns)

    setup_orchestrations_pass_through()
    setup_direction_never_terminates("again")

    # when
    actual_result = await bounded_run_management_service.process_prompt(random_prompt)

    # then: capped at the configured bound, and no answer was delivered.
    assert "out of turns" in actual_result
    assert data_coordination_service.recall.mock_calls == [call(ANY)] * configured_max_turns


async def test_should_refuse_gracefully_when_review_never_passes_on_process_prompt(
        run_management_service,
        data_coordination_service,
        decision_coordination_service,
        direction_coordination_service,
        create_random_string):

    # given
    random_prompt = create_random_string()
    expected_result = "I can't help with that at the moment."

    data_coordination_service.recall.side_effect = lambda context: context

    decision_coordination_service.think.side_effect = lambda context: dataclasses.replace(
        context, status=AgentStatus.REVISING)

    # when
    actual_result = await run_management_service.process_prompt(random_prompt)

    # then
    assert actual_result == expected_result
    assert decision_coordination_service.think.mock_calls == [call(ANY)] * 7
    assert direction_coordination_service.act.mock_calls == []


async def test_should_remember_preference_on_process_prompt_when_decision_sets_remember(
        run_management_service,
        data_coordination_service,
        decision_coordination_service,
        direction_coordination_service,
        create_random_string):

    # given
    random_prompt = create_random_string()
    preference = create_random_string()

    data_coordination_service.recall.side_effect = lambda context: context

    decision_coordination_service.think.side_effect = lambda context: dataclasses.replace(
        context, remember=preference)

    direction_coordination_service.act.side_effect = lambda context: dataclasses.replace(
        context, result="done", status=AgentStatus.RESPONDED)

    # when
    await run_management_service.process_prompt(random_prompt)

    # then
    assert data_coordination_service.remember.mock_calls == [call(preference)]


async def test_should_recall_every_turn_on_process_prompt(
        run_management_service,
        data_coordination_service,
        decision_coordination_service,
        direction_coordination_service,
        create_random_string):

    # given
    random_prompt = create_random_string()
    turns = 0

    data_coordination_service.recall.side_effect = lambda context: context
    decision_coordination_service.think.side_effect = lambda context: context

    def act(context: AgentContext) -> AgentContext:
        nonlocal turns
        turns += 1

        if turns < 3:
            return dataclasses.replace(context, result="working", status=AgentStatus.WORKING)

        return dataclasses.replace(context, result="done", status=AgentStatus.RESPONDED)

    direction_coordination_service.act.side_effect = act

    # when
    actual_result = await run_management_service.process_prompt(random_prompt)

    # then
    assert actual_result == "done"
    assert data_coordination_service.recall.mock_calls == [call(ANY)] * 3


async def test_should_reset_log_on_process_prompt(
        run_management_service,
        logging_broker,
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
    assert logging_broker.log_reset.mock_calls == [call()]
