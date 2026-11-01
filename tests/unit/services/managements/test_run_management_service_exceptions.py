# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.coordinations.agents.exceptions import (
    AgentCoordinationValidationException,
    InvalidAgentException)


@pytest.mark.parametrize("invalid_prompt", [None, "", " "])
async def test_should_throw_validation_exception_on_process_prompt_if_prompt_is_invalid_and_log_it(
        invalid_prompt,
        run_management_service,
        data_coordination_service,
        logging_broker,
        same_exception_as):

    # given
    invalid_agent_exception = InvalidAgentException(
        message="Invalid prompt. Please correct the error and try again.")

    expected_exception = AgentCoordinationValidationException(
        message="Agent coordination validation error occurred, fix the error and try again.",
        inner_exception=invalid_agent_exception)

    # when
    with pytest.raises(AgentCoordinationValidationException) as raised:
        await run_management_service.process_prompt(invalid_prompt)

    # then
    assert raised.value.same_exception_as(expected_exception)
    assert logging_broker.mock_calls == [call.log_error(same_exception_as(expected_exception))]
    assert data_coordination_service.mock_calls == []
