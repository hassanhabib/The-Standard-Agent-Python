# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.returns.exceptions import (
    InvalidReturnException,
    ReturnValidationException)


@pytest.mark.parametrize("invalid_payload", [None, "", " "])
async def test_should_throw_validation_exception_on_return_if_payload_is_invalid_and_log_it(
        invalid_payload, return_service, logging_broker, same_exception_as):

    # given
    invalid_return_exception = InvalidReturnException(
        message="Invalid return payload. Please correct the error and try again.")

    expected_return_validation_exception = ReturnValidationException(
        message="Return validation error occurred, fix the error and try again.",
        inner_exception=invalid_return_exception)

    # when
    with pytest.raises(ReturnValidationException) as raised:
        await return_service.return_payload(invalid_payload)

    # then
    assert raised.value.same_exception_as(expected_return_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_return_validation_exception))]
