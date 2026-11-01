# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import ANY, call

from standard_agents.models.orchestrations.agents.agent_context import AgentContext


async def test_should_narrate_processes_to_logging_broker_on_act(
        direction_coordination_service,
        internal_tool_service,
        logging_broker,
        containing):

    # given
    input_context = AgentContext(prompt="prompt", direction_type="calculator", payload="1+1")
    internal_tool_service.handles.return_value = True
    internal_tool_service.run.return_value = "2"

    # when
    await direction_coordination_service.act(input_context)

    # then
    narrated_tool_output = call.log_payload(
        "Direction", containing("Tool"), containing("2"), detail=ANY)

    assert logging_broker.mock_calls.count(narrated_tool_output) == 1
