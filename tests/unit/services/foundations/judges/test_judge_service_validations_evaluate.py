# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.foundations.judges.exceptions import (
    InvalidJudgeException,
    JudgeValidationException)
from tests.unit.services.foundations.judges.judge_service_tests import JudgeServiceTests


class TestJudgeServiceValidationsEvaluate(JudgeServiceTests):
    @pytest.mark.parametrize("invalid_text", [None, "", "   "])
    def test_should_raise_validation_exception_on_evaluate_if_inputs_are_invalid_and_log_it(
        self,
        invalid_text: str) -> None:

        # given
        invalid_judge_exception = InvalidJudgeException(
            message="Invalid judge. Please correct the errors and try again.")

        invalid_judge_exception.upsert_data_list("task", "Text is required")
        invalid_judge_exception.upsert_data_list("candidate", "Text is required")

        expected_judge_validation_exception = JudgeValidationException(
            message="Judge validation error occurred, fix the errors and try again.",
            inner_exception=invalid_judge_exception)

        # when
        with pytest.raises(JudgeValidationException) as actual_judge_validation_exception:
            asyncio.run(self.judge_service.evaluate(invalid_text, invalid_text))

        # then
        assert expected_judge_validation_exception.same_exception_as(
            actual_judge_validation_exception.value)

        self.assert_logged_once("log_error", expected_judge_validation_exception)
        assert self.verifier_broker_mock.mock_calls == []
