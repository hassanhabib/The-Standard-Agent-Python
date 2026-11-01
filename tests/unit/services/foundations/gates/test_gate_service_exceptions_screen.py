# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.gates.exceptions import (
    FailedGateDependencyException,
    GateDependencyException)
from tests.unit.services.foundations.gates.gate_service_tests import GateServiceTests


class TestGateServiceExceptionsScreen(GateServiceTests):
    @pytest.mark.parametrize("dependency_error", [
        OSError("classifier unreachable"),
        RuntimeError("classifier failed")
    ])
    def test_should_raise_dependency_exception_on_screen_if_dependency_error_occurs_and_log_it(
        self,
        dependency_error: Exception) -> None:

        # given
        input_text = self.create_random_string()

        failed_gate_dependency_exception = FailedGateDependencyException(
            message="Failed gate dependency error occurred, contact support.",
            inner_exception=dependency_error)

        expected_gate_dependency_exception = GateDependencyException(
            message="Gate dependency error occurred, contact support.",
            inner_exception=failed_gate_dependency_exception)

        self.classifier_broker_mock.classify.side_effect = dependency_error

        # when
        with pytest.raises(GateDependencyException) as actual_gate_dependency_exception:
            asyncio.run(self.gate_service.screen(input_text))

        # then
        assert expected_gate_dependency_exception.same_exception_as(
            actual_gate_dependency_exception.value)

        assert self.classifier_broker_mock.mock_calls == [call.classify(input_text)]
        self.assert_logged_once("log_error", expected_gate_dependency_exception)
