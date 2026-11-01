# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationValidationException,
    NullAgentContextException)


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
