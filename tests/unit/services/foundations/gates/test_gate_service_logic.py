# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call


async def test_should_screen(
        gate_service, classifier_broker, logging_broker, create_random_string):

    # given
    random_input = create_random_string()
    random_verdict = create_random_string()
    input_input = random_input
    expected_verdict = random_verdict
    classifier_broker.classify.return_value = random_verdict

    # when
    actual_verdict = await gate_service.screen(input_input)

    # then
    assert actual_verdict == expected_verdict
    assert classifier_broker.mock_calls == [call.classify(input_input)]
    assert logging_broker.mock_calls == []
