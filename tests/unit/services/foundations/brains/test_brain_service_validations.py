# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.brains.exceptions import (
    BrainValidationException,
    InvalidBrainException)


@pytest.mark.parametrize("invalid_user_prompt", [None, "", " "])
async def test_should_throw_validation_exception_on_generate_if_user_prompt_is_invalid_and_log_it(
        invalid_user_prompt,
        brain_service,
        generator_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_system_prompt = create_random_string()

    invalid_brain_exception = InvalidBrainException(
        message="Invalid brain input. Please correct the error and try again.")

    expected_brain_validation_exception = BrainValidationException(
        message="Brain validation error occurred, fix the error and try again.",
        inner_exception=invalid_brain_exception)

    # when
    with pytest.raises(BrainValidationException) as raised:
        await brain_service.generate(random_system_prompt, invalid_user_prompt)

    # then
    assert raised.value.same_exception_as(expected_brain_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_brain_validation_exception))]

    assert generator_broker.mock_calls == []
