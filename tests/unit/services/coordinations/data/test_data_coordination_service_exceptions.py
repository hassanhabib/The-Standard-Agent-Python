# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.knowledges.exceptions import (
    KnowledgeValidationException)
from standard_agents.models.foundations.memories.exceptions import MemoryValidationException
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationValidationException,
    NullAgentContextException)
from xeptions import Xeption


def _dependency_validation_exceptions() -> list[Xeption]:
    return [
        MemoryValidationException(
            message="memory validation",
            inner_exception=Xeption(message="inner")),

        KnowledgeValidationException(
            message="knowledge validation",
            inner_exception=Xeption(message="inner"))]


DEPENDENCY_VALIDATION_EXCEPTION_IDS = ["memory-validation", "knowledge-validation"]


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


@pytest.mark.parametrize(
    "foundation_exception",
    _dependency_validation_exceptions(),
    ids=DEPENDENCY_VALIDATION_EXCEPTION_IDS)
async def test_should_throw_dependency_validation_exception_on_recall_if_dependency_validation_error_occurs_and_log_it(
        foundation_exception,
        data_coordination_service,
        skill_service,
        logging_broker,
        same_exception_as,
        create_random_agent_context):
    # given
    input_context = create_random_agent_context()

    expected_exception = AgentOrchestrationDependencyValidationException(
        message="Agent orchestration dependency validation error occurred, "
                "fix the error and try again.",
        inner_exception=foundation_exception.inner_exception)

    skill_service.retrieve_skills.side_effect = foundation_exception

    # when
    with pytest.raises(AgentOrchestrationDependencyValidationException) as raised:
        await data_coordination_service.recall(input_context)

    # then
    assert raised.value.same_exception_as(expected_exception)

    # The prompt is announced before anything is fetched, so a failure still says which prompt
    # Data was working on.
    assert logging_broker.mock_calls == [
        call.log_payload("Data", "Received prompt", input_context.prompt, detail=False),
        call.log_error(same_exception_as(expected_exception))]
