# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from restfulsense import (
    HttpRequestException,
    HttpResponseBadRequestException,
    HttpResponseForbiddenException,
    HttpResponseInternalServerErrorException,
    HttpResponseNotFoundException,
    HttpResponseServiceUnavailableException,
    HttpResponseUnauthorizedException,
    HttpResponseUrlNotFoundException)
from standard_agents.models.foundations.gates.exceptions import (
    FailedGateDependencyException,
    GateDependencyException,
    GateDependencyValidationException,
    InvalidGateException)


def _gate_dependency_exception(inner_exception: Exception) -> GateDependencyException:
    failed_gate_dependency_exception = FailedGateDependencyException(
        message="Failed gate dependency error occurred, contact support.",
        inner_exception=inner_exception)

    return GateDependencyException(
        message="Gate dependency error occurred, contact support.",
        inner_exception=failed_gate_dependency_exception)


async def test_should_throw_dependency_validation_exception_on_screen_if_bad_request_error_occurs_and_log_it(
        gate_service, classifier_broker, logging_broker, same_exception_as, create_random_string):

    # given
    random_input = create_random_string()
    bad_request_exception = HttpResponseBadRequestException()

    invalid_gate_exception = InvalidGateException(
        message="Invalid gate request. Please correct the error and try again.")

    expected_gate_dependency_validation_exception = GateDependencyValidationException(
        message="Gate dependency validation error occurred, fix the error and try again.",
        inner_exception=invalid_gate_exception)

    classifier_broker.classify.side_effect = bad_request_exception

    # when
    with pytest.raises(GateDependencyValidationException) as raised:
        await gate_service.screen(random_input)

    # then
    assert raised.value.same_exception_as(expected_gate_dependency_validation_exception)
    assert classifier_broker.mock_calls == [call.classify(random_input)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_gate_dependency_validation_exception))]


@pytest.mark.parametrize(
    "critical_dependency_exception",
    [
        HttpResponseUnauthorizedException(),
        HttpResponseForbiddenException(),
        HttpResponseNotFoundException(),
        HttpResponseUrlNotFoundException(),
        HttpRequestException(),
    ],
    ids=["unauthorized", "forbidden", "not-found", "url-not-found", "http-request"])
async def test_should_throw_critical_dependency_exception_on_screen_if_critical_error_occurs_and_log_it(
        critical_dependency_exception,
        gate_service,
        classifier_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_input = create_random_string()
    expected_gate_dependency_exception = _gate_dependency_exception(
        critical_dependency_exception)

    classifier_broker.classify.side_effect = critical_dependency_exception

    # when
    with pytest.raises(GateDependencyException) as raised:
        await gate_service.screen(random_input)

    # then
    assert raised.value.same_exception_as(expected_gate_dependency_exception)
    assert classifier_broker.mock_calls == [call.classify(random_input)]

    assert logging_broker.mock_calls == [
        call.log_critical(same_exception_as(expected_gate_dependency_exception))]


@pytest.mark.parametrize(
    "dependency_exception",
    [HttpResponseInternalServerErrorException(), HttpResponseServiceUnavailableException()],
    ids=["internal-server-error", "service-unavailable"])
async def test_should_throw_dependency_exception_on_screen_if_dependency_error_occurs_and_log_it(
        dependency_exception,
        gate_service,
        classifier_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_input = create_random_string()
    expected_gate_dependency_exception = _gate_dependency_exception(dependency_exception)
    classifier_broker.classify.side_effect = dependency_exception

    # when
    with pytest.raises(GateDependencyException) as raised:
        await gate_service.screen(random_input)

    # then
    assert raised.value.same_exception_as(expected_gate_dependency_exception)
    assert classifier_broker.mock_calls == [call.classify(random_input)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_gate_dependency_exception))]
