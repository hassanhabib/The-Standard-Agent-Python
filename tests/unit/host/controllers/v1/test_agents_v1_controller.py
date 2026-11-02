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

import dataclasses
from http import HTTPStatus
from unittest.mock import ANY, call

from standard_agents.host.controllers.action_results import ObjectResult
from standard_agents.host.models.v1.agent_run_request_v1 import AgentRunRequestV1
from standard_agents.host.models.v1.agent_run_response_v1 import AgentRunResponseV1
from standard_agents.host.models.v1.failure_v1 import FailureV1
from standard_agents.host.models.v1.pending_effect_v1 import PendingEffectV1
from standard_agents.models.clients.agents.agent_failure import AgentFailure
from standard_agents.models.clients.agents.agent_failure_category import AgentFailureCategory
from standard_agents.models.clients.agents.agent_failure_codes import AgentFailureCodes
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel


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


async def test_should_post_run_and_carry_the_pending_effect(agent, agents_v1_controller):
    # given: a run held on an authority, waiting on the caller's tool call
    request = AgentRunRequestV1(prompt="wire the money", session_id="trip-3")
    principal = AgentPrincipal(id="hassan", tenant_id="peerllm")

    held_effect = dataclasses.replace(
        AgentEffect.create(
            run_id="run-9",
            tool_name="wire",
            arguments='{"amount":100}',
            risk_level=RiskLevel.IRREVERSIBLE,
            approval_required=True,
            principal=principal,
            scope="account:42"),
        call_id="call-7")

    agent.run.return_value = AgentOutcome(
        result="waiting on an authority",
        status=AgentStatus.AWAITING_APPROVAL,
        pending_effect=held_effect)

    expected_result = ObjectResult(
        HTTPStatus.OK,
        AgentRunResponseV1(
            result="waiting on an authority",
            status="AwaitingApproval",
            pending_effect=PendingEffectV1(
                run_id="run-9",
                call_id="call-7",
                tool_name="wire",
                arguments='{"amount":100}',
                scope="account:42",
                risk_level="Irreversible",
                approval_required=True,
                idempotency_key=held_effect.idempotency_key,
                principal="hassan")))

    # when
    actual_result = await agents_v1_controller.post_run(request)

    # then: the act the run is waiting on crossed the wire whole, key and call id included
    assert actual_result == expected_result


async def test_should_post_run_and_carry_the_failure(agent, agents_v1_controller):
    # given: a run that stopped without an answer, and says why as a code
    request = AgentRunRequestV1(prompt="loop forever", session_id="trip-3")

    failure = AgentFailure(
        category=AgentFailureCategory.SERVICE,
        code=AgentFailureCodes.TURNS_EXHAUSTED,
        message="I ran out of turns before finishing.")

    agent.run.return_value = AgentOutcome(
        result="I ran out of turns before finishing.",
        status=AgentStatus.WORKING,
        failure=failure)

    expected_result = ObjectResult(
        HTTPStatus.OK,
        AgentRunResponseV1(
            result="I ran out of turns before finishing.",
            status="Working",
            pending_effect=None,
            failure=FailureV1(
                category="Service",
                code="turns_exhausted",
                message="I ran out of turns before finishing.")))

    # when
    actual_result = await agents_v1_controller.post_run(request)

    # then: the code crossed the wire, so a caller across HTTP decides on it, not the sentence
    assert actual_result == expected_result
