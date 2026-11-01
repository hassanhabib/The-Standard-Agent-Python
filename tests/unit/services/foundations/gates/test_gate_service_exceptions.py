# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from restfulsense import HttpResponseBadRequestException
from standard_agents.models.foundations.gates.exceptions import (
    GateDependencyValidationException,
    InvalidGateException)


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
