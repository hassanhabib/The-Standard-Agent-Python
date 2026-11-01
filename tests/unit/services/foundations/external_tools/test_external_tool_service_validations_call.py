# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolValidationException,
    InvalidExternalToolException)
from tests.unit.services.foundations.external_tools.external_tool_service_tests import (
    ExternalToolServiceTests)


class TestExternalToolServiceValidationsCall(ExternalToolServiceTests):
    @pytest.mark.parametrize("invalid_name", [None, "", "   "])
    def test_should_raise_validation_exception_on_call_if_name_is_invalid_and_log_it(
        self,
        invalid_name: str) -> None:

        # given
        input_payload = self.create_random_string()

        invalid_external_tool_exception = InvalidExternalToolException(
            message="Invalid external tool. Please correct the errors and try again.")

        invalid_external_tool_exception.upsert_data_list("name", "Text is required")

        expected_exception = ExternalToolValidationException(
            message="External tool validation error occurred, fix the errors and try again.",
            inner_exception=invalid_external_tool_exception)

        # when
        with pytest.raises(ExternalToolValidationException) as actual_exception:
            asyncio.run(self.external_tool_service.call(invalid_name, input_payload))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
        assert self.mcp_broker_mock.mock_calls == []
