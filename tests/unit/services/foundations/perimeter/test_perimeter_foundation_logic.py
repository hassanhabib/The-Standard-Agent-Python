# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

from standard_agents.brokers.approvals.approval_broker import ApprovalDecision
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision)


async def test_should_authorize_effect(
        policy_service, policy_broker, logging_broker, create_random_effect):

    # given
    random_effect = create_random_effect()
    expected_decision = AuthorizationDecision.deny("not permitted")
    policy_broker.authorize.return_value = expected_decision

    # when: the decision must be the broker's, unchanged. A foundation that softened a denial
    # would be deciding policy, which is not its job.
    actual_decision = await policy_service.authorize_effect(random_effect)

    # then
    assert actual_decision == expected_decision
    assert policy_broker.mock_calls == [call.authorize(random_effect)]
    assert logging_broker.mock_calls == []


async def test_should_request_approval(
        approval_service, approval_broker, logging_broker, create_random_effect):

    # given
    random_effect = create_random_effect()
    expected_decision = ApprovalDecision.PENDING
    approval_broker.request.return_value = expected_decision

    # when
    actual_decision = await approval_service.request_approval(random_effect)

    # then: PENDING must survive the trip. Turning it into anything else here is the one mistake
    # that would let an unanswered approval look like consent.
    assert actual_decision is expected_decision
    assert approval_broker.mock_calls == [call.request(random_effect)]
    assert logging_broker.mock_calls == []
