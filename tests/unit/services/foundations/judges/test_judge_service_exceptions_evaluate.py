# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.judges.exceptions import (
    FailedJudgeDependencyException,
    JudgeDependencyException)
from tests.unit.services.foundations.judges.judge_service_tests import JudgeServiceTests


class TestJudgeServiceExceptionsEvaluate(JudgeServiceTests):
    @pytest.mark.parametrize("dependency_error", [
        OSError("verifier unreachable"),
        RuntimeError("verifier failed")
    ])
    def test_should_raise_dependency_exception_on_evaluate_if_dependency_error_occurs_and_log_it(
        self,
        dependency_error: Exception) -> None:

        # given
        input_task = self.create_random_string()
        input_candidate = self.create_random_string()

        failed_judge_dependency_exception = FailedJudgeDependencyException(
            message="Failed judge dependency error occurred, contact support.",
            inner_exception=dependency_error)

        expected_judge_dependency_exception = JudgeDependencyException(
            message="Judge dependency error occurred, contact support.",
            inner_exception=failed_judge_dependency_exception)

        self.verifier_broker_mock.verify.side_effect = dependency_error

        # when
        with pytest.raises(JudgeDependencyException) as actual_judge_dependency_exception:
            asyncio.run(self.judge_service.evaluate(input_task, input_candidate))

        # then
        assert expected_judge_dependency_exception.same_exception_as(
            actual_judge_dependency_exception.value)

        assert self.verifier_broker_mock.mock_calls == [
            call.verify(input_task, input_candidate)
        ]

        self.assert_logged_once("log_error", expected_judge_dependency_exception)
