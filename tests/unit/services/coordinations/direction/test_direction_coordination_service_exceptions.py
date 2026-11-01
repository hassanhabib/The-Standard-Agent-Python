# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyException,
    ExternalToolValidationException)
from standard_agents.models.foundations.internal_tools.exceptions import (
    InternalToolDependencyException,
    InternalToolServiceException,
    InternalToolValidationException)
from standard_agents.models.foundations.returns.exceptions import ReturnServiceException
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    AgentOrchestrationValidationException,
    FailedAgentOrchestrationServiceException,
    NullAgentContextException)
from xeptions import Xeption


def _dependency_validation_exceptions() -> list[Xeption]:
    return [
        InternalToolValidationException(
            message="internal tool validation",
            inner_exception=Xeption(message="inner")),

        ExternalToolValidationException(
            message="external tool validation",
            inner_exception=Xeption(message="inner"))]


def _dependency_exceptions() -> list[Xeption]:
    return [
        InternalToolDependencyException(
            message="internal tool dependency",
            inner_exception=Xeption(message="inner")),

        InternalToolServiceException(
            message="internal tool service",
            inner_exception=Xeption(message="inner")),

        ExternalToolDependencyException(
            message="external tool dependency",
            inner_exception=Xeption(message="inner")),

        ReturnServiceException(
            message="return service",
            inner_exception=Xeption(message="inner"))]


async def test_should_throw_validation_exception_on_act_if_context_is_null_and_log_it(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        return_service,
        logging_broker,
        same_exception_as):

    # given
    null_context = None

    null_agent_context_exception = NullAgentContextException(message="Agent context is null.")

    expected_agent_orchestration_validation_exception = AgentOrchestrationValidationException(
        message="Agent orchestration validation error occurred, fix the error and try again.",
        inner_exception=null_agent_context_exception)

    # when
    with pytest.raises(AgentOrchestrationValidationException) as raised:
        await direction_coordination_service.act(null_context)

    # then
    assert raised.value.same_exception_as(expected_agent_orchestration_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_agent_orchestration_validation_exception))]

    assert internal_tool_service.mock_calls == []
    assert external_tool_service.mock_calls == []
    assert return_service.mock_calls == []


@pytest.mark.parametrize(
    "foundation_exception",
    _dependency_validation_exceptions(),
    ids=["internal-tool-validation", "external-tool-validation"])
async def test_should_throw_dependency_validation_exception_on_act_if_dependency_validation_error_occurs_and_log_it(
        foundation_exception,
        direction_coordination_service,
        internal_tool_service,
        logging_broker,
        create_context_with_direction,
        same_exception_as):

    # given
    input_context = create_context_with_direction("calculator", "1+1")

    expected_exception = AgentOrchestrationDependencyValidationException(
        message="Agent orchestration dependency validation error occurred, "
                "fix the error and try again.",
        inner_exception=foundation_exception.inner_exception)

    internal_tool_service.handles.side_effect = foundation_exception

    # when
    with pytest.raises(AgentOrchestrationDependencyValidationException) as raised:
        await direction_coordination_service.act(input_context)

    # then
    assert raised.value.same_exception_as(expected_exception)
    assert logging_broker.mock_calls == [call.log_error(same_exception_as(expected_exception))]


@pytest.mark.parametrize(
    "foundation_exception",
    _dependency_exceptions(),
    ids=["internal-tool-dependency", "internal-tool-service", "external-tool-dependency",
         "return-service"])
async def test_should_throw_dependency_exception_on_act_if_dependency_error_occurs_and_log_it(
        foundation_exception,
        direction_coordination_service,
        internal_tool_service,
        logging_broker,
        create_context_with_direction,
        same_exception_as):

    # given
    input_context = create_context_with_direction("calculator", "1+1")

    expected_exception = AgentOrchestrationDependencyException(
        message="Agent orchestration dependency error occurred, contact support.",
        inner_exception=foundation_exception.inner_exception)

    internal_tool_service.handles.side_effect = foundation_exception

    # when
    with pytest.raises(AgentOrchestrationDependencyException) as raised:
        await direction_coordination_service.act(input_context)

    # then
    assert raised.value.same_exception_as(expected_exception)
    assert logging_broker.mock_calls == [call.log_error(same_exception_as(expected_exception))]


async def test_should_throw_service_exception_on_act_if_service_error_occurs_and_log_it(
        direction_coordination_service,
        internal_tool_service,
        logging_broker,
        create_context_with_direction,
        same_exception_as):

    # given
    input_context = create_context_with_direction("calculator", "1+1")
    service_exception = Exception()

    failed_agent_orchestration_service_exception = FailedAgentOrchestrationServiceException(
        message="Failed agent orchestration service error occurred, contact support.",
        inner_exception=service_exception)

    expected_exception = AgentOrchestrationServiceException(
        message="Agent orchestration service error occurred, contact support.",
        inner_exception=failed_agent_orchestration_service_exception)

    internal_tool_service.handles.side_effect = service_exception

    # when
    with pytest.raises(AgentOrchestrationServiceException) as raised:
        await direction_coordination_service.act(input_context)

    # then
    assert raised.value.same_exception_as(expected_exception)
    assert logging_broker.mock_calls == [call.log_error(same_exception_as(expected_exception))]
