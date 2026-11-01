# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.internal_tools.exceptions import (
    FailedInternalToolDependencyException,
    InternalToolDependencyException)
from tests.unit.services.foundations.internal_tools.internal_tool_service_tests import (
    InternalToolServiceTests)


class TestInternalToolServiceExceptionsRun(InternalToolServiceTests):
    # The tool is the dependency: a name nobody registered (KeyError) and a tool that broke while
    # acting are both failures of what the service depends on, not of the service itself.
    @pytest.mark.parametrize("tool_error", [
        KeyError("unknown tool"),
        Exception("tool broke")
    ])
    def test_should_raise_dependency_exception_on_run_if_tool_error_occurs_and_log_it(
        self,
        tool_error: Exception) -> None:

        # given
        input_name = self.create_random_string()
        input_payload = self.create_random_string()

        failed_internal_tool_dependency_exception = FailedInternalToolDependencyException(
            message="Failed internal tool dependency error occurred, contact support.",
            inner_exception=tool_error)

        expected_internal_tool_dependency_exception = InternalToolDependencyException(
            message="Internal tool dependency error occurred, contact support.",
            inner_exception=failed_internal_tool_dependency_exception)

        self.tool_broker_mock.run.side_effect = tool_error

        # when
        with pytest.raises(InternalToolDependencyException) as actual_exception:
            asyncio.run(self.internal_tool_service.run(input_name, input_payload))

        # then
        assert expected_internal_tool_dependency_exception.same_exception_as(
            actual_exception.value)

        assert self.tool_broker_mock.mock_calls == [call.run(input_name, input_payload)]
        self.assert_logged_once("log_error", expected_internal_tool_dependency_exception)
