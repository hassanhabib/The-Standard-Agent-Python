# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from restfulsense.exceptions import (
    HttpRequestException,
    HttpResponseBadRequestException,
    HttpResponseForbiddenException,
    HttpResponseNotFoundException,
    HttpResponseUnauthorizedException,
    HttpResponseUrlNotFoundException)
from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyException,
    BrainDependencyValidationException,
    FailedBrainDependencyException,
    InvalidBrainException,
    UnreachableBrainException)


def _brain_dependency_exception(inner_exception: Exception) -> BrainDependencyException:
    failed_brain_dependency_exception = FailedBrainDependencyException(
        message="Failed brain dependency error occurred, contact support.",
        inner_exception=inner_exception)

    return BrainDependencyException(
        message="Brain dependency error occurred, contact support.",
        inner_exception=failed_brain_dependency_exception)


def _unreachable_brain_exception(
        http_request_exception: HttpRequestException) -> BrainDependencyException:

    unreachable_brain_exception = UnreachableBrainException(
        message="Nothing answered at the brain's address. Check that the address is right "
            "and that the service is running.",
        inner_exception=http_request_exception)

    return BrainDependencyException(
        message="Brain dependency error occurred, contact support.",
        inner_exception=unreachable_brain_exception)


async def test_should_throw_dependency_validation_exception_on_generate_if_bad_request_error_occurs_and_log_it(
        brain_service,
        generator_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_system_prompt = create_random_string()
    random_user_prompt = create_random_string()
    bad_request_exception = HttpResponseBadRequestException()

    invalid_brain_exception = InvalidBrainException(
        message="Invalid brain request. Please correct the error and try again.")

    expected_brain_dependency_validation_exception = BrainDependencyValidationException(
        message="Brain dependency validation error occurred, fix the error and try again.",
        inner_exception=invalid_brain_exception)

    generator_broker.generate.side_effect = bad_request_exception

    # when
    with pytest.raises(BrainDependencyValidationException) as raised:
        await brain_service.generate(random_system_prompt, random_user_prompt)

    # then
    assert raised.value.same_exception_as(expected_brain_dependency_validation_exception)

    assert generator_broker.mock_calls == [
        call.generate(random_system_prompt, random_user_prompt)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_brain_dependency_validation_exception))]


@pytest.mark.parametrize(
    "critical_dependency_exception",
    [
        HttpResponseUnauthorizedException(),
        HttpResponseForbiddenException(),
        HttpResponseNotFoundException(),
        HttpResponseUrlNotFoundException(),
    ],
    ids=["unauthorized", "forbidden", "not-found", "url-not-found"])
async def test_should_throw_critical_dependency_exception_on_generate_if_critical_error_occurs_and_log_it(
        critical_dependency_exception,
        brain_service,
        generator_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_system_prompt = create_random_string()
    random_user_prompt = create_random_string()

    expected_brain_dependency_exception = _brain_dependency_exception(
        critical_dependency_exception)

    generator_broker.generate.side_effect = critical_dependency_exception

    # when
    with pytest.raises(BrainDependencyException) as raised:
        await brain_service.generate(random_system_prompt, random_user_prompt)

    # then
    assert raised.value.same_exception_as(expected_brain_dependency_exception)

    assert generator_broker.mock_calls == [
        call.generate(random_system_prompt, random_user_prompt)]

    assert logging_broker.mock_calls == [
        call.log_critical(same_exception_as(expected_brain_dependency_exception))]


async def test_should_throw_critical_dependency_exception_on_generate_if_nothing_answered_and_log_it(
        brain_service,
        generator_broker,
        logging_broker,
        same_exception_as,
        create_random_string):
    """A refused connection, a name that resolves to nothing, a request that never left the machine.

    The person's next step is the address, not support (SPEC.md 4.10, v1.14).
    """
    # given
    random_system_prompt = create_random_string()
    random_user_prompt = create_random_string()
    http_request_exception = HttpRequestException()
    expected_brain_dependency_exception = _unreachable_brain_exception(http_request_exception)
    generator_broker.generate.side_effect = http_request_exception

    # when
    with pytest.raises(BrainDependencyException) as raised:
        await brain_service.generate(random_system_prompt, random_user_prompt)

    # then
    assert raised.value.same_exception_as(expected_brain_dependency_exception)

    assert generator_broker.mock_calls == [
        call.generate(random_system_prompt, random_user_prompt)]

    assert logging_broker.mock_calls == [
        call.log_critical(same_exception_as(expected_brain_dependency_exception))]
