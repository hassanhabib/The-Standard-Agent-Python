# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolValidationException,
    InvalidExternalToolException)


@pytest.mark.parametrize("invalid_name", [None, "", " "])
async def test_should_throw_validation_exception_on_call_if_name_is_invalid_and_log_it(
        invalid_name,
        external_tool_service,
        mcp_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_input = create_random_string()

    invalid_external_tool_exception = InvalidExternalToolException(
        message="Invalid external tool. Please correct the error and try again.")

    expected_external_tool_validation_exception = ExternalToolValidationException(
        message="External tool validation error occurred, fix the error and try again.",
        inner_exception=invalid_external_tool_exception)

    # when
    with pytest.raises(ExternalToolValidationException) as raised:
        await external_tool_service.call(invalid_name, random_input)

    # then
    assert raised.value.same_exception_as(expected_external_tool_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_external_tool_validation_exception))]

    assert mcp_broker.mock_calls == []
