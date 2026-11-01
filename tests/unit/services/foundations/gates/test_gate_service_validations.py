# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.gates.exceptions import (
    GateValidationException,
    InvalidGateException)


def _gate_validation_exception() -> GateValidationException:
    invalid_gate_exception = InvalidGateException(
        message="Invalid gate input. Please correct the error and try again.")

    return GateValidationException(
        message="Gate validation error occurred, fix the error and try again.",
        inner_exception=invalid_gate_exception)


@pytest.mark.parametrize("invalid_input", [None, "", " "])
async def test_should_throw_validation_exception_on_screen_if_input_is_invalid_and_log_it(
        invalid_input, gate_service, classifier_broker, logging_broker, same_exception_as):

    # given
    expected_gate_validation_exception = _gate_validation_exception()

    # when
    with pytest.raises(GateValidationException) as raised:
        await gate_service.screen(invalid_input)

    # then
    assert raised.value.same_exception_as(expected_gate_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_gate_validation_exception))]

    assert classifier_broker.mock_calls == []


@pytest.mark.parametrize("invalid_instructions", [None, "", "   "])
async def test_should_throw_validation_exception_on_detect_conflict_if_instructions_invalid_and_log_it(
        invalid_instructions, gate_service, classifier_broker, logging_broker, same_exception_as):

    # given
    expected_gate_validation_exception = _gate_validation_exception()

    # when
    with pytest.raises(GateValidationException) as raised:
        await gate_service.detect_conflict(invalid_instructions)

    # then
    assert raised.value.same_exception_as(expected_gate_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_gate_validation_exception))]

    assert classifier_broker.mock_calls == []
