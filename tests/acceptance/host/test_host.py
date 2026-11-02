# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Found in the 2026-09-04 principal review (F-20): every host test called a controller by hand, so
# routing, JSON binding, the API-key middleware, content types and the SSE wire could all regress
# while the suite stayed green. These stand the real host up and speak HTTP to it. The agent
# behind the door is a double: the host is the unit here, and the loop has its own suite.

from unittest.mock import ANY, call

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


async def test_should_round_trip_a_held_run_through_http(
        agent,
        serve_host,
        full_request_document,
        expected_prompt_request,
        held_effect):

    # given: the full V1 request in, a run held on an authority out
    agent.run.return_value = AgentOutcome(
        result="waiting on an authority",
        status=AgentStatus.AWAITING_APPROVAL,
        pending_effect=held_effect)

    expected_response = {
        "result": "waiting on an authority",
        "status": "AwaitingApproval",
        "pendingEffect": {
            "runId": "run-9",
            "callId": "call-7",
            "toolName": "wire",
            "arguments": '{"amount":100}',
            "scope": "account:42",
            "riskLevel": "Irreversible",
            "approvalRequired": True,
            "idempotencyKey": held_effect.idempotency_key,
            "principal": "hassan",
        },
        "failure": None,
    }

    async with serve_host() as client:
        # when
        response = await client.post_json("api/V1/agents/runs", full_request_document)

    # then: every field survived the JSON wire in both directions, the pending act included
    assert response.status == 200
    assert response.media_type == "application/json"
    assert response.json() == expected_response
    assert agent.run.call_args_list == [call(expected_prompt_request, cancellation=ANY)]


async def test_should_bind_a_prompt_only_document_with_empty_lists_through_http(agent, serve_host):
    # given: the smallest V1 document a caller can post
    agent.run.return_value = AgentOutcome("the answer", AgentStatus.RESPONDED)
    expected_prompt_request = PromptRequest(prompt="what is owed")

    async with serve_host() as client:
        # when
        response = await client.post(
            "api/V1/agents/runs",
            '{"prompt":"what is owed"}',
            "application/json; charset=utf-8")

    # then: an absent list is an empty one, and an absent option is unset
    assert response.status == 200
    assert agent.run.call_args_list == [call(expected_prompt_request, cancellation=ANY)]
