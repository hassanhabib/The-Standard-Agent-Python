# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationValidationException,
    NullAgentContextException)


async def test_should_throw_validation_exception_on_recall_if_context_is_null_and_log_it(
        data_coordination_service,
        skill_service,
        memory_service,
        knowledge_service,
        logging_broker,
        same_exception_as):
    # given
    null_context = None

    null_agent_context_exception = NullAgentContextException(
        message="Agent context is null.")

    expected_agent_orchestration_validation_exception = AgentOrchestrationValidationException(
        message="Agent orchestration validation error occurred, fix the error and try again.",
        inner_exception=null_agent_context_exception)

    # when
    with pytest.raises(AgentOrchestrationValidationException) as raised:
        await data_coordination_service.recall(null_context)

    # then
    assert raised.value.same_exception_as(expected_agent_orchestration_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_agent_orchestration_validation_exception))]

    assert skill_service.mock_calls == []
    assert memory_service.mock_calls == []
    assert knowledge_service.mock_calls == []
