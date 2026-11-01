# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.foundations.gates.exceptions import (
    GateValidationException,
    InvalidGateException)
from tests.unit.services.foundations.gates.gate_service_tests import GateServiceTests


class TestGateServiceValidationsScreen(GateServiceTests):
    @pytest.mark.parametrize("invalid_text", [None, "", "   "])
    def test_should_raise_validation_exception_on_screen_if_text_is_invalid_and_log_it(
        self,
        invalid_text: str) -> None:

        # given
        invalid_gate_exception = InvalidGateException(
            message="Invalid gate. Please correct the errors and try again.")

        invalid_gate_exception.upsert_data_list("text", "Text is required")

        expected_gate_validation_exception = GateValidationException(
            message="Gate validation error occurred, fix the errors and try again.",
            inner_exception=invalid_gate_exception)

        # when
        with pytest.raises(GateValidationException) as actual_gate_validation_exception:
            asyncio.run(self.gate_service.screen(self.create_random_string(), invalid_text))

        # then
        assert expected_gate_validation_exception.same_exception_as(
            actual_gate_validation_exception.value)

        self.assert_logged_once("log_error", expected_gate_validation_exception)
        assert self.classifier_broker_mock.mock_calls == []
