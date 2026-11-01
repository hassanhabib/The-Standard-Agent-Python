# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolValidationException)
from standard_agents.models.foundations.internal_tools.exceptions import (
    InternalToolValidationException)
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationValidationException,
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
