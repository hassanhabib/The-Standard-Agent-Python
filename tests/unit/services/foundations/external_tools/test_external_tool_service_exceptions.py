# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from restfulsense import HttpResponseBadRequestException
from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyValidationException,
    InvalidExternalToolException)


async def test_should_throw_dependency_validation_exception_on_call_if_bad_request_error_occurs_and_log_it(
        external_tool_service,
        mcp_broker,
        logging_broker,
        same_exception_as,
        create_random_string,
        expected_arguments_json):

    # given
    random_name = create_random_string()
    random_input = create_random_string()
    bad_request_exception = HttpResponseBadRequestException()

    invalid_external_tool_exception = InvalidExternalToolException(
        message="Invalid external tool request. Please correct the error and try again.")

    expected_external_tool_dependency_validation_exception = (
        ExternalToolDependencyValidationException(
            message="External tool dependency validation error occurred, "
                    "fix the error and try again.",
            inner_exception=invalid_external_tool_exception))

    mcp_broker.call.side_effect = bad_request_exception

    # when
    with pytest.raises(ExternalToolDependencyValidationException) as raised:
        await external_tool_service.call(random_name, random_input)

    # then
    assert raised.value.same_exception_as(expected_external_tool_dependency_validation_exception)

    assert mcp_broker.mock_calls == [
        call.call(random_name, expected_arguments_json(random_input))]

    assert logging_broker.mock_calls == [
        call.log_error(
            same_exception_as(expected_external_tool_dependency_validation_exception))]


async def test_should_throw_dependency_validation_exception_on_retrieve_tools_if_bad_request_error_occurs_and_log_it(
        external_tool_service, mcp_broker, logging_broker, same_exception_as):

    # given
    http_response_bad_request_exception = HttpResponseBadRequestException()

    invalid_external_tool_exception = InvalidExternalToolException(
        message="Invalid external tool request. Please correct the error and try again.")

    invalid_external_tool_exception.add_data(http_response_bad_request_exception.data)

    expected_external_tool_dependency_validation_exception = (
        ExternalToolDependencyValidationException(
            message="External tool dependency validation error occurred, "
                    "fix the error and try again.",
            inner_exception=invalid_external_tool_exception))

    mcp_broker.list_tools.side_effect = http_response_bad_request_exception

    # when
    with pytest.raises(ExternalToolDependencyValidationException) as raised:
        await external_tool_service.retrieve_tools()

    # then
    assert raised.value.same_exception_as(expected_external_tool_dependency_validation_exception)
    assert mcp_broker.mock_calls == [call.list_tools()]

    assert logging_broker.mock_calls == [
        call.log_error(
            same_exception_as(expected_external_tool_dependency_validation_exception))]
