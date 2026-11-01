# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from restfulsense.exceptions import HttpResponseBadRequestException
from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyValidationException,
    InvalidBrainException)


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
