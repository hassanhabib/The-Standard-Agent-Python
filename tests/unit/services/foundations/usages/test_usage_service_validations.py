# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.usages.exceptions import (
    InvalidUsageException,
    UsageValidationException)


def _usage_validation_exception(message: str) -> UsageValidationException:
    invalid_usage_exception = InvalidUsageException(message=message)

    return UsageValidationException(
        message="Usage validation error occurred, fix the error and try again.",
        inner_exception=invalid_usage_exception)


async def test_should_throw_validation_exception_on_measure_if_prompt_is_null(
        usage_service, usage_broker, logging_broker, same_exception_as, create_random_string):

    # given
    expected_usage_validation_exception = _usage_validation_exception(
        "Invalid usage, prompt is required. Please correct the error and try again.")

    # when
    with pytest.raises(UsageValidationException) as raised:
        await usage_service.measure(prompt=None, completion=create_random_string())

    # then
    assert raised.value.same_exception_as(expected_usage_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_usage_validation_exception))]

    assert usage_broker.mock_calls == []


async def test_should_throw_validation_exception_on_measure_if_completion_is_null(
        usage_service, usage_broker, logging_broker, same_exception_as, create_random_string):

    # given
    expected_usage_validation_exception = _usage_validation_exception(
        "Invalid usage, completion is required. Please correct the error and try again.")

    # when
    with pytest.raises(UsageValidationException) as raised:
        await usage_service.measure(prompt=create_random_string(), completion=None)

    # then
    assert raised.value.same_exception_as(expected_usage_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_usage_validation_exception))]

    assert usage_broker.mock_calls == []


async def test_should_throw_validation_exception_on_measure_if_count_is_negative(
        usage_service, usage_broker, logging_broker, same_exception_as, create_random_string):
    """A custom counter is host code, so a negative count is reachable.

    A negative count SUBTRACTS from the run's spend, which turns a budget into something an
    unusual reply can extend rather than exhaust.
    """
    # given
    expected_usage_validation_exception = _usage_validation_exception(
        "Invalid usage, token count cannot be negative. Please correct the error and try again.")

    usage_broker.count_tokens.return_value = -1

    # when
    with pytest.raises(UsageValidationException) as raised:
        await usage_service.measure(create_random_string(), create_random_string())

    # then
    assert raised.value.same_exception_as(expected_usage_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_usage_validation_exception))]
