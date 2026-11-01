# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.coordinations.agents.exceptions import (
    AgentCoordinationDependencyException,
    AgentCoordinationValidationException,
    InvalidAgentException)
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationServiceException)
from xeptions import Xeption

DEPENDENCY_EXCEPTIONS = [
    AgentOrchestrationDependencyException(
        message="orchestration dependency",
        inner_exception=Xeption(message="inner")),

    AgentOrchestrationServiceException(
        message="orchestration service",
        inner_exception=Xeption(message="inner"))]


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


@pytest.mark.parametrize("orchestration_exception", DEPENDENCY_EXCEPTIONS)
async def test_should_throw_dependency_exception_on_process_prompt_if_dependency_error_occurs_and_log_it(
        orchestration_exception,
        run_management_service,
        data_coordination_service,
        logging_broker,
        create_random_string,
        same_exception_as):

    # given
    random_prompt = create_random_string()

    expected_exception = AgentCoordinationDependencyException(
        message="Agent coordination dependency error occurred, contact support.",
        inner_exception=orchestration_exception.inner_exception)

    data_coordination_service.recall.side_effect = orchestration_exception

    # when
    with pytest.raises(AgentCoordinationDependencyException) as raised:
        await run_management_service.process_prompt(random_prompt)

    # then
    assert raised.value.same_exception_as(expected_exception)
    assert logging_broker.log_error.mock_calls == [call(same_exception_as(expected_exception))]
