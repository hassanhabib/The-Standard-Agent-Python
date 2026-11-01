# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import math
from unittest.mock import ANY, call

import pytest

from standard_agents.models.foundations.judges.exceptions import (
    InvalidJudgeException,
    InvalidJudgeScoreException,
    JudgeValidationException)


@pytest.mark.parametrize("invalid_candidate", [None, "", " "])
async def test_should_throw_validation_exception_on_evaluate_if_candidate_is_invalid_and_log_it(
        invalid_candidate,
        judge_service,
        verifier_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    invalid_judge_exception = InvalidJudgeException(
        message="Invalid judge input. Please correct the error and try again.")

    expected_judge_validation_exception = JudgeValidationException(
        message="Judge validation error occurred, fix the error and try again.",
        inner_exception=invalid_judge_exception)

    # when
    with pytest.raises(JudgeValidationException) as raised:
        await judge_service.evaluate(create_random_string(), invalid_candidate)

    # then
    assert raised.value.same_exception_as(expected_judge_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_judge_validation_exception))]

    assert verifier_broker.mock_calls == []


@pytest.mark.parametrize(
    "non_numeric_verdict",
    [
        None,
        "",
        " ",
        "allow",
        "ACTION: calculator: 47 * 89",
        "I would rate this a 9 out of 10.",
    ])
async def test_should_throw_validation_exception_on_evaluate_if_score_is_not_numeric_and_log_it(
        non_numeric_verdict,
        judge_service,
        verifier_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_candidate = create_random_string()

    invalid_judge_score_exception = InvalidJudgeScoreException(
        message="Invalid judge score. Score must be a number between 0.0 and 1.0.")

    expected_judge_validation_exception = JudgeValidationException(
        message="Judge validation error occurred, fix the error and try again.",
        inner_exception=invalid_judge_score_exception)

    verifier_broker.verify.return_value = non_numeric_verdict

    # when
    with pytest.raises(JudgeValidationException) as raised:
        await judge_service.evaluate(create_random_string(), random_candidate)

    # then
    assert raised.value.same_exception_as(expected_judge_validation_exception)
    assert verifier_broker.mock_calls == [call.verify(ANY, random_candidate)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_judge_validation_exception))]


@pytest.mark.parametrize("out_of_range_score", [-0.1, 1.1, 87.0, math.nan])
async def test_should_throw_validation_exception_on_evaluate_if_score_is_out_of_range_and_log_it(
        out_of_range_score,
        judge_service,
        verifier_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_candidate = create_random_string()
    verdict = str(out_of_range_score)

    invalid_judge_score_exception = InvalidJudgeScoreException(
        message="Invalid judge score. Score must be between 0.0 and 1.0.")

    expected_judge_validation_exception = JudgeValidationException(
        message="Judge validation error occurred, fix the error and try again.",
        inner_exception=invalid_judge_score_exception)

    verifier_broker.verify.return_value = verdict

    # when
    with pytest.raises(JudgeValidationException) as raised:
        await judge_service.evaluate(create_random_string(), random_candidate)

    # then
    assert raised.value.same_exception_as(expected_judge_validation_exception)
    assert verifier_broker.mock_calls == [call.verify(ANY, random_candidate)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_judge_validation_exception))]
