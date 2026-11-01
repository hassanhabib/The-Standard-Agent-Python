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
