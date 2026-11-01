# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import ANY, call

from standard_agents.models.foundations.usages.agent_usage import AgentUsage


async def test_should_narrate_brain_reply_content_on_think_stream(
        decision_coordination_service,
        brain_service,
        logging_broker,
        create_random_agent_context,
        setup_gate_allows,
        setup_judge_approves,
        to_async_stream,
        drain,
        containing):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate_stream.return_value = to_async_stream("FINAL: my-secret-answer")

    # when
    await drain(decision_coordination_service.think_stream(input_context))

    # then
    expected_brain_reply_call = call(
        "Decision", containing("Brain"), containing("my-secret-answer"), detail=ANY)

    assert logging_broker.log_payload.mock_calls.count(expected_brain_reply_call) == 1


async def test_should_narrate_gate_accept_verdict_on_think_stream(
        decision_coordination_service,
        gate_service,
        brain_service,
        logging_broker,
        create_random_agent_context,
        setup_judge_approves,
        to_async_stream,
        drain,
        containing):

    # given
    input_context = create_random_agent_context()
    setup_judge_approves()
    gate_service.screen.return_value = "allow because the request is safe"
    brain_service.generate_stream.return_value = to_async_stream("FINAL: 42")

    # when
    await drain(decision_coordination_service.think_stream(input_context))

    # then
    expected_gate_accept_call = call(
        "Decision", containing("ACCEPT"), containing("safe"), detail=ANY)

    assert logging_broker.log_payload.mock_calls.count(expected_gate_accept_call) == 1


async def test_should_narrate_gate_refusal_reason_on_think_stream(
        decision_coordination_service,
        gate_service,
        logging_broker,
        create_random_agent_context,
        drain,
        containing):

    # given
    input_context = create_random_agent_context()
    gate_service.screen.return_value = "refuse: asks for personal information"

    # when
    await drain(decision_coordination_service.think_stream(input_context))

    # then
    expected_gate_refusal_call = call(
        "Decision", containing("REFUSE"), containing("personal information"), detail=ANY)

    assert logging_broker.log_payload.mock_calls.count(expected_gate_refusal_call) == 1


async def test_should_narrate_gate_route_and_proceed_on_think_stream(
        decision_coordination_service,
        gate_service,
        brain_service,
        logging_broker,
        create_random_agent_context,
        setup_judge_approves,
        to_async_stream,
        drain,
        containing):

    # given
    input_context = create_random_agent_context()
    setup_judge_approves()
    gate_service.screen.return_value = "route: arithmetic"
    brain_service.generate_stream.return_value = to_async_stream("FINAL: 42")

    # when
    decision_stream = decision_coordination_service.think_stream(input_context)
    await drain(decision_stream)

    # then a route proceeds to the Brain (not refused) and is narrated as ROUTE
    assert decision_stream.result.direction_type == "ReturnResponse"

    expected_gate_route_call = call(
        "Decision", containing("ROUTE"), containing("arithmetic"), detail=ANY)

    assert logging_broker.log_payload.mock_calls.count(expected_gate_route_call) == 1


async def test_should_narrate_processes_to_logging_broker_on_think_stream(
        decision_coordination_service,
        brain_service,
        logging_broker,
        create_random_agent_context,
        setup_gate_allows,
        setup_judge_approves,
        to_async_stream,
        drain,
        containing):

    # given
    input_context = create_random_agent_context()
    setup_gate_allows()
    setup_judge_approves()
    brain_service.generate_stream.return_value = to_async_stream("FINAL: 42")

    # when
    await drain(decision_coordination_service.think_stream(input_context))

    # then
    expected_gate_call = call("Decision", containing("Gate"), ANY, detail=ANY)
    expected_judge_call = call("Decision", containing("Judge"))

    assert logging_broker.log_payload.mock_calls.count(expected_gate_call) == 1
    assert logging_broker.log_process.mock_calls.count(expected_judge_call) == 1
