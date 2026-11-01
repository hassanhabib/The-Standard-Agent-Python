# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.judges.exceptions import (
    FailedJudgeDependencyException,
    InvalidJudgementException,
    JudgeDependencyValidationException,
    FailedJudgeServiceException,
    JudgeDependencyException,
    JudgeServiceException)
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
        input_judge_prompt = self.create_random_string()
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
            asyncio.run(self.judge_service.evaluate(input_judge_prompt, input_task, input_candidate))

        # then
        assert expected_judge_dependency_exception.same_exception_as(
            actual_judge_dependency_exception.value)

        assert self.verifier_broker_mock.mock_calls == [
            call.verify(input_judge_prompt, input_task, input_candidate)
        ]

        self.assert_logged_once("log_error", expected_judge_dependency_exception)

    # ValueError is what an unreadable verdict ("great!" where a score belongs) raises; it has no
    # category of its own, so it lands in the catch-all with everything else unexpected.
    @pytest.mark.parametrize("service_error", [
        Exception("verifier broke"),
        ValueError("could not convert string to float")
    ])
    def test_should_raise_service_exception_on_evaluate_if_service_error_occurs_and_log_it(
        self,
        service_error: Exception) -> None:

        # given
        input_judge_prompt = self.create_random_string()
        input_task = self.create_random_string()
        input_candidate = self.create_random_string()

        failed_judge_service_exception = FailedJudgeServiceException(
            message="Failed judge service error occurred, contact support.",
            inner_exception=service_error)

        expected_judge_service_exception = JudgeServiceException(
            message="Judge service error occurred, contact support.",
            inner_exception=failed_judge_service_exception)

        self.verifier_broker_mock.verify.side_effect = service_error

        # when
        with pytest.raises(JudgeServiceException) as actual_judge_service_exception:
            asyncio.run(self.judge_service.evaluate(input_judge_prompt, input_task, input_candidate))

        # then
        assert expected_judge_service_exception.same_exception_as(
            actual_judge_service_exception.value)

        assert self.verifier_broker_mock.mock_calls == [
            call.verify(input_judge_prompt, input_task, input_candidate)
        ]

        self.assert_logged_once("log_error", expected_judge_service_exception)

    # SPEC.md 4.2: the score is a number between 0.0 and 1.0, and the Judge validates its range.
    # A verifier that answers outside it handed back something invalid, which is the dependency's
    # fault, not the caller's.
    @pytest.mark.parametrize("out_of_range_score", ["-0.1", "1.01", "7"])
    def test_should_raise_dependency_validation_exception_on_evaluate_if_score_is_out_of_range_and_log_it(
        self,
        out_of_range_score: str) -> None:

        # given
        input_judge_prompt = self.create_random_string()
        input_task = self.create_random_string()
        input_candidate = self.create_random_string()

        invalid_judgement_exception = InvalidJudgementException(
            message="Invalid judgement. Please correct the errors and try again.")

        invalid_judgement_exception.upsert_data_list(
            "score",
            "Value must be between 0.0 and 1.0")

        expected_exception = JudgeDependencyValidationException(
            message="Judge dependency validation error occurred, fix the errors and try again.",
            inner_exception=invalid_judgement_exception)

        self.verifier_broker_mock.verify.return_value = f"SCORE: {out_of_range_score}\nREASON: x"

        # when
        with pytest.raises(JudgeDependencyValidationException) as actual_exception:
            asyncio.run(
                self.judge_service.evaluate(input_judge_prompt, input_task, input_candidate))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
