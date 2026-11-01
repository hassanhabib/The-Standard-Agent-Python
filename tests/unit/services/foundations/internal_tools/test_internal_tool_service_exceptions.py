# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.internal_tools.exceptions import (
    FailedInternalToolDependencyException,
    FailedInternalToolServiceException,
    InternalToolDependencyException,
    InternalToolServiceException)


def _internal_tool_dependency_exception(
        inner_exception: Exception) -> InternalToolDependencyException:

    failed_internal_tool_dependency_exception = FailedInternalToolDependencyException(
        message="Failed internal tool dependency error occurred, contact support.",
        inner_exception=inner_exception)

    return InternalToolDependencyException(
        message="Internal tool dependency error occurred, contact support.",
        inner_exception=failed_internal_tool_dependency_exception)


async def test_should_throw_dependency_exception_on_run_if_tool_error_occurs_and_log_it(
        internal_tool_service,
        tool_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    input_name = create_random_string()
    input_input = create_random_string()
    tool_exception = RuntimeError()

    expected_internal_tool_dependency_exception = _internal_tool_dependency_exception(
        tool_exception)

    tool_broker.run.side_effect = tool_exception

    # when
    with pytest.raises(InternalToolDependencyException) as raised:
        await internal_tool_service.run(input_name, input_input)

    # then
    assert raised.value.same_exception_as(expected_internal_tool_dependency_exception)
    assert tool_broker.mock_calls == [call.run(input_name, input_input)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_internal_tool_dependency_exception))]


async def test_should_throw_dependency_exception_on_run_if_tool_is_not_found_and_log_it(
        internal_tool_service,
        tool_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    input_name = create_random_string()
    input_input = create_random_string()
    key_error = KeyError()

    expected_internal_tool_dependency_exception = _internal_tool_dependency_exception(
        key_error)

    tool_broker.run.side_effect = key_error

    # when
    with pytest.raises(InternalToolDependencyException) as raised:
        await internal_tool_service.run(input_name, input_input)

    # then
    assert raised.value.same_exception_as(expected_internal_tool_dependency_exception)
    assert tool_broker.mock_calls == [call.run(input_name, input_input)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_internal_tool_dependency_exception))]


async def test_should_throw_service_exception_on_handles_if_service_error_occurs_and_log_it(
        internal_tool_service,
        tool_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    input_name = create_random_string()
    service_exception = Exception()

    failed_internal_tool_service_exception = FailedInternalToolServiceException(
        message="Failed internal tool service error occurred, contact support.",
        inner_exception=service_exception)

    expected_internal_tool_service_exception = InternalToolServiceException(
        message="Internal tool service error occurred, contact support.",
        inner_exception=failed_internal_tool_service_exception)

    tool_broker.has.side_effect = service_exception

    # when
    with pytest.raises(InternalToolServiceException) as raised:
        await internal_tool_service.handles(input_name)

    # then
    assert raised.value.same_exception_as(expected_internal_tool_service_exception)
    assert tool_broker.mock_calls == [call.has(input_name)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_internal_tool_service_exception))]
