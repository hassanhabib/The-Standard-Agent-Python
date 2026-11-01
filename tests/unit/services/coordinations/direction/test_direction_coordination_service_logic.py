# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

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
