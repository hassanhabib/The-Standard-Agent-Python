# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.judges.exceptions import (
    InvalidJudgeException,
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
