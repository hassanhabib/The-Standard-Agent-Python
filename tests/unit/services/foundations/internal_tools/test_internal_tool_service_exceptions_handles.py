# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.internal_tools.exceptions import (
    FailedInternalToolServiceException,
    InternalToolServiceException)
from tests.unit.services.foundations.internal_tools.internal_tool_service_tests import (
    InternalToolServiceTests)


class TestInternalToolServiceExceptionsHandles(InternalToolServiceTests):
    def test_should_raise_service_exception_on_handles_if_service_error_occurs_and_log_it(
        self) -> None:

        # given
        input_name = self.create_random_string()
        service_error = Exception(self.create_random_string())

        failed_internal_tool_service_exception = FailedInternalToolServiceException(
            message="Failed internal tool service error occurred, contact support.",
            inner_exception=service_error)

        expected_internal_tool_service_exception = InternalToolServiceException(
            message="Internal tool service error occurred, contact support.",
            inner_exception=failed_internal_tool_service_exception)

        self.tool_broker_mock.has.side_effect = service_error

        # when
        with pytest.raises(InternalToolServiceException) as actual_exception:
            asyncio.run(self.internal_tool_service.handles(input_name))

        # then
        assert expected_internal_tool_service_exception.same_exception_as(
            actual_exception.value)

        assert self.tool_broker_mock.mock_calls == [call.has(input_name)]
        self.assert_logged_once("log_error", expected_internal_tool_service_exception)
