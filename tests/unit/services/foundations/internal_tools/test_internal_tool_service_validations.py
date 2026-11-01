# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.internal_tools.exceptions import (
    InternalToolValidationException,
    InvalidInternalToolException)


def _internal_tool_validation_exception() -> InternalToolValidationException:
    invalid_internal_tool_exception = InvalidInternalToolException(
        message="Invalid internal tool. Please correct the error and try again.")

    return InternalToolValidationException(
        message="Internal tool validation error occurred, fix the error and try again.",
        inner_exception=invalid_internal_tool_exception)


@pytest.mark.parametrize("invalid_name", [None, "", " "])
async def test_should_throw_validation_exception_on_handles_if_name_is_invalid_and_log_it(
        invalid_name, internal_tool_service, tool_broker, logging_broker, same_exception_as):

    # given
    expected_internal_tool_validation_exception = _internal_tool_validation_exception()

    # when
    with pytest.raises(InternalToolValidationException) as raised:
        await internal_tool_service.handles(invalid_name)

    # then
    assert raised.value.same_exception_as(expected_internal_tool_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_internal_tool_validation_exception))]

    assert tool_broker.mock_calls == []


@pytest.mark.parametrize("invalid_name", [None, "", " "])
async def test_should_throw_validation_exception_on_run_if_name_is_invalid_and_log_it(
        invalid_name,
        internal_tool_service,
        tool_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_input = create_random_string()
    expected_internal_tool_validation_exception = _internal_tool_validation_exception()

    # when
    with pytest.raises(InternalToolValidationException) as raised:
        await internal_tool_service.run(invalid_name, random_input)

    # then
    assert raised.value.same_exception_as(expected_internal_tool_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_internal_tool_validation_exception))]

    assert tool_broker.mock_calls == []
