# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The reason these foundations exist.

Each resource failure must arrive named after its own resource; otherwise a full disk gets blamed
on the orchestration that happened to ask.
"""

from unittest.mock import call

import pytest

from restfulsense import HttpRequestException
from standard_agents.models.foundations.policies.exceptions import (
    FailedPolicyDependencyException,
    PolicyDependencyException)


async def test_should_throw_dependency_exception_on_authorize_if_policy_engine_is_unreachable(
        policy_service, policy_broker, logging_broker, create_random_effect, same_exception_as):

    # given
    random_effect = create_random_effect()
    http_request_exception = HttpRequestException()

    failed_policy_dependency_exception = FailedPolicyDependencyException(
        message="Failed policy dependency error occurred, contact support.",
        inner_exception=http_request_exception)

    expected_policy_dependency_exception = PolicyDependencyException(
        message="Policy dependency error occurred, contact support.",
        inner_exception=failed_policy_dependency_exception)

    policy_broker.authorize.side_effect = http_request_exception

    # when
    with pytest.raises(PolicyDependencyException) as raised:
        await policy_service.authorize_effect(random_effect)

    # then
    assert raised.value.same_exception_as(expected_policy_dependency_exception)
    assert policy_broker.mock_calls == [call.authorize(random_effect)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_policy_dependency_exception))]
