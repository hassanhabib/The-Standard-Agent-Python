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
