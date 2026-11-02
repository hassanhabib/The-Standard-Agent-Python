# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# An exposer is pure mapping over one service dependency, so its tests are mapping tests: success
# in, protocol out; invalid in, 400 out; nothing else in between.

from http import HTTPStatus
from unittest.mock import ANY, call

from standard_agents.host.controllers.action_results import ObjectResult
from standard_agents.host.models.agent_run_request import AgentRunRequest
from standard_agents.host.models.agent_run_response import AgentRunResponse
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


async def test_should_post_run(agent, agents_controller):
    # given
    request = AgentRunRequest(prompt="what is owed")
    agent.run.return_value = AgentOutcome("the answer", AgentStatus.RESPONDED)

    expected_result = ObjectResult(
        status_code=HTTPStatus.OK,
        value=AgentRunResponse(result="the answer", status="Responded"))

    # when
    actual_result = await agents_controller.post_run(request)

    # then
    assert actual_result == expected_result
    assert agent.mock_calls == [call.run("what is owed", cancellation=ANY)]
