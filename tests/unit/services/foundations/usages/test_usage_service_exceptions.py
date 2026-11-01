# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from restfulsense import HttpRequestException
from standard_agents.models.foundations.usages.exceptions import (
    FailedUsageDependencyException,
    UsageDependencyException)


async def test_should_throw_dependency_exception_on_measure_if_counter_is_unreachable(
        usage_service, usage_broker, logging_broker, same_exception_as, create_random_string):
    """A counter that cannot be reached is the COUNTER's failure, not the measurement's.

    The caller can carry on with a provider-reported number when it has one, but only if the
    failure names the dependency rather than being flattened into a service error.
    """
    # given
    http_request_exception = HttpRequestException()

    failed_usage_dependency_exception = FailedUsageDependencyException(
        message="Failed usage dependency error occurred, contact support.",
        inner_exception=http_request_exception)

    expected_usage_dependency_exception = UsageDependencyException(
        message="Usage dependency error occurred, contact support.",
        inner_exception=failed_usage_dependency_exception)

    usage_broker.count_tokens.side_effect = http_request_exception

    # when
    with pytest.raises(UsageDependencyException) as raised:
        await usage_service.measure(create_random_string(), create_random_string())

    # then
    assert raised.value.same_exception_as(expected_usage_dependency_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_usage_dependency_exception))]
