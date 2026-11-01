# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyException,
    FailedExternalToolDependencyException)
from tests.unit.services.foundations.external_tools.external_tool_service_tests import (
    ExternalToolServiceTests)


class TestExternalToolServiceExceptionsCall(ExternalToolServiceTests):
    # A server that refused, could not be reached, or ended mid-answer: all OSError, and all
    # surfaced through the same categorized path as any other dependency failure (SPEC.md 4.8).
    @pytest.mark.parametrize("dependency_error", [
        ConnectionRefusedError("server refused"),
        TimeoutError("server did not answer"),
        OSError("server unreachable")
    ])
    def test_should_raise_dependency_exception_on_call_if_server_error_occurs_and_log_it(
        self,
        dependency_error: Exception) -> None:

        # given
        input_name = self.create_random_string()
        input_payload = self.create_random_string()

        failed_dependency_exception = FailedExternalToolDependencyException(
            message="Failed external tool dependency error occurred, contact support.",
            inner_exception=dependency_error)

        expected_exception = ExternalToolDependencyException(
            message="External tool dependency error occurred, contact support.",
            inner_exception=failed_dependency_exception)

        self.mcp_broker_mock.call.side_effect = dependency_error

        # when
        with pytest.raises(ExternalToolDependencyException) as actual_exception:
            asyncio.run(self.external_tool_service.call(input_name, input_payload))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        assert self.mcp_broker_mock.mock_calls == [call.call(input_name, input_payload)]
        self.assert_logged_once("log_error", expected_exception)
