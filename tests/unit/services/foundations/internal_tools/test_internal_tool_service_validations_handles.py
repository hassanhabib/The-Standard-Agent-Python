# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.foundations.internal_tools.exceptions import (
    InternalToolValidationException,
    InvalidInternalToolException)
from tests.unit.services.foundations.internal_tools.internal_tool_service_tests import (
    InternalToolServiceTests)


class TestInternalToolServiceValidationsHandles(InternalToolServiceTests):
    @pytest.mark.parametrize("invalid_name", [None, "", "   "])
    def test_should_raise_validation_exception_on_handles_if_name_is_invalid_and_log_it(
        self,
        invalid_name: str) -> None:

        # given
        invalid_internal_tool_exception = InvalidInternalToolException(
            message="Invalid internal tool. Please correct the errors and try again.")

        invalid_internal_tool_exception.upsert_data_list("name", "Text is required")

        expected_internal_tool_validation_exception = InternalToolValidationException(
            message="Internal tool validation error occurred, fix the errors and try again.",
            inner_exception=invalid_internal_tool_exception)

        # when
        with pytest.raises(InternalToolValidationException) as actual_exception:
            asyncio.run(self.internal_tool_service.handles(invalid_name))

        # then
        assert expected_internal_tool_validation_exception.same_exception_as(
            actual_exception.value)

        self.assert_logged_once("log_error", expected_internal_tool_validation_exception)
        assert self.tool_broker_mock.mock_calls == []
