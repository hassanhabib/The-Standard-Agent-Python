# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Found in the 2026-09-04 principal review (F-10): the host's wire carried a prompt alone and
# answered with a result and a status alone, so sessions, caller transcripts, caller tools,
# approval continuation and pending effects could not cross the HTTP boundary. Version 1 of the
# wire is the whole request and the whole outcome. An exposer is pure mapping over one dependency,
# so these are mapping tests: the wire in, the contract out; the outcome in, the wire out; invalid
# in, 400 out.

from http import HTTPStatus
from unittest.mock import ANY, call

from standard_agents.host.controllers.action_results import ObjectResult
from standard_agents.host.models.v1.agent_run_response_v1 import AgentRunResponseV1
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


async def test_should_post_run(
        agent,
        agents_v1_controller,
        full_request,
        expected_prompt_request):

    # given
    agent.run.return_value = AgentOutcome("the answer", AgentStatus.RESPONDED)

    expected_result = ObjectResult(
        HTTPStatus.OK,
        AgentRunResponseV1(result="the answer", status="Responded", pending_effect=None))

    # when
    actual_result = await agents_v1_controller.post_run(full_request)

    # then: every field of the wire reached the contract, and the outcome reached the wire
    assert actual_result == expected_result
    assert agent.mock_calls == [call.run(expected_prompt_request, cancellation=ANY)]
