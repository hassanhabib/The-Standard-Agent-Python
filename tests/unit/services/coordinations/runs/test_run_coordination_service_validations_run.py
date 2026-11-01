# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.coordinations.runs.exceptions import (
    InvalidRunException,
    RunCoordinationValidationException)
from tests.unit.services.coordinations.runs.run_coordination_service_tests import (
    RunCoordinationServiceTests)


class TestRunCoordinationServiceValidationsRun(RunCoordinationServiceTests):
    @pytest.mark.parametrize("invalid_prompt", [None, "", "   "])
    def test_should_raise_validation_exception_on_run_if_prompt_is_invalid_and_log_it(
        self,
        invalid_prompt: str) -> None:

        # given
        invalid_run_exception = InvalidRunException(
            message="Invalid run. Please correct the errors and try again.")

        invalid_run_exception.upsert_data_list("prompt", "Text is required")

        expected_exception = RunCoordinationValidationException(
            message="Run coordination validation error occurred, fix the errors and try again.",
            inner_exception=invalid_run_exception)

        # when
        with pytest.raises(RunCoordinationValidationException) as actual_exception:
            asyncio.run(self.run_coordination_service.run(invalid_prompt))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
        assert self.data_orchestration_service_mock.mock_calls == []
        assert self.decision_orchestration_service_mock.mock_calls == []
        assert self.direction_orchestration_service_mock.mock_calls == []
