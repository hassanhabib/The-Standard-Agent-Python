# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.foundations.returns.exceptions import (
    InvalidReturnException,
    ReturnValidationException)
from tests.unit.services.foundations.returns.return_service_tests import ReturnServiceTests


class TestReturnServiceValidationsReturnPayload(ReturnServiceTests):
    @pytest.mark.parametrize("invalid_payload", [None, "", "   "])
    def test_should_raise_validation_exception_on_return_if_payload_is_invalid_and_log_it(
        self,
        invalid_payload: str) -> None:

        # given
        invalid_return_exception = InvalidReturnException(
            message="Invalid return. Please correct the errors and try again.")

        invalid_return_exception.upsert_data_list("payload", "Text is required")

        expected_return_validation_exception = ReturnValidationException(
            message="Return validation error occurred, fix the errors and try again.",
            inner_exception=invalid_return_exception)

        # when
        with pytest.raises(ReturnValidationException) as actual_exception:
            asyncio.run(self.return_service.return_payload(invalid_payload))

        # then
        assert expected_return_validation_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_return_validation_exception)
