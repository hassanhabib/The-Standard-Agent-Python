# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import ANY, call

import pytest


@pytest.mark.parametrize("score", [0.0, 0.3, 1.0])
async def test_should_evaluate(
        score, judge_service, verifier_broker, logging_broker, create_random_string):

    # given
    random_candidate = create_random_string()
    verdict = str(score)
    expected_score = score
    verifier_broker.verify.return_value = verdict

    # when
    actual_judgement = await judge_service.evaluate(create_random_string(), random_candidate)

    # then
    assert actual_judgement.score == expected_score
    assert verifier_broker.mock_calls == [call.verify(ANY, random_candidate)]
    assert logging_broker.mock_calls == []


async def test_should_pass_the_task_to_the_verifier_on_evaluate(
        judge_service, verifier_broker, logging_broker, create_random_string):
    """SPEC.md 4.2: an answer is good or bad FOR a question.

    A Judge handed only the candidate scores a fit it cannot see, and the failure is silent: it
    still returns a plausible number, still rejects, and still spends a turn of the loop's budget
    on a revision it could not have reasoned about.
    """
    # given
    random_task = create_random_string()
    random_candidate = create_random_string()
    verifier_broker.verify.return_value = "1.0"

    # when
    await judge_service.evaluate(random_task, random_candidate)

    # then
    assert verifier_broker.mock_calls == [call.verify(random_task, random_candidate)]
    assert logging_broker.mock_calls == []


@pytest.mark.parametrize(("verdict", "expected_score"), [(" 0.75 ", 0.75), ("0.5\n", 0.5)])
async def test_should_parse_surrounding_whitespace_on_evaluate(
        verdict,
        expected_score,
        judge_service,
        verifier_broker,
        logging_broker,
        create_random_string):

    # given
    random_candidate = create_random_string()
    verifier_broker.verify.return_value = verdict

    # when
    actual_judgement = await judge_service.evaluate(create_random_string(), random_candidate)

    # then
    assert actual_judgement.score == expected_score
    assert verifier_broker.mock_calls == [call.verify(ANY, random_candidate)]
    assert logging_broker.mock_calls == []


async def test_should_parse_score_and_reason_on_evaluate(
        judge_service, verifier_broker, logging_broker, create_random_string):

    # given
    random_candidate = create_random_string()
    verdict = "SCORE: 0.4\nREASON: it never states the year"
    verifier_broker.verify.return_value = verdict

    # when
    actual_judgement = await judge_service.evaluate(create_random_string(), random_candidate)

    # then
    assert actual_judgement.score == 0.4
    assert actual_judgement.reason == "it never states the year"
    assert verifier_broker.mock_calls == [call.verify(ANY, random_candidate)]
    assert logging_broker.mock_calls == []
