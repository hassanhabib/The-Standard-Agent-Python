# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyException,
    BrainDependencyValidationException,
    BrainValidationException)
from standard_agents.models.foundations.gates.exceptions import (
    GateDependencyException,
    GateServiceException,
    GateValidationException)
from standard_agents.models.foundations.judges.exceptions import (
    JudgeDependencyException,
    JudgeValidationException)
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    AgentOrchestrationValidationException,
    FailedAgentOrchestrationServiceException,
    NullAgentContextException)
from xeptions import Xeption

DEPENDENCY_VALIDATION_EXCEPTIONS = [
    GateValidationException(
        message="gate validation",
        inner_exception=Xeption(message="inner")),

    BrainValidationException(
        message="brain validation",
        inner_exception=Xeption(message="inner")),

    JudgeValidationException(
        message="judge validation",
        inner_exception=Xeption(message="inner")),

    BrainDependencyValidationException(
        message="brain dependency validation",
        inner_exception=Xeption(message="inner"))]

DEPENDENCY_EXCEPTIONS = [
    GateDependencyException(
        message="gate dependency",
        inner_exception=Xeption(message="inner")),

    GateServiceException(
        message="gate service",
        inner_exception=Xeption(message="inner")),

    BrainDependencyException(
        message="brain dependency",
        inner_exception=Xeption(message="inner")),

    JudgeDependencyException(
        message="judge dependency",
        inner_exception=Xeption(message="inner"))]


def _exception_id(exception: Xeption) -> str:
    return type(exception).__name__


async def test_should_throw_validation_exception_on_think_if_context_is_null_and_log_it(
        decision_coordination_service,
        gate_service,
        brain_service,
        judge_service,
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
        await decision_coordination_service.think(null_context)

    # then
    assert raised.value.same_exception_as(expected_agent_orchestration_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_agent_orchestration_validation_exception))]

    assert gate_service.screen.mock_calls == []
    assert gate_service.mock_calls == []
    assert brain_service.mock_calls == []
    assert judge_service.mock_calls == []
