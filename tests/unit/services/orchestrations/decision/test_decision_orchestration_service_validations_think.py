# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.orchestrations.decision.exceptions import (
    DecisionOrchestrationValidationException,
    NullAgentContextException)
from tests.unit.services.orchestrations.decision.decision_orchestration_service_tests import (
    DecisionOrchestrationServiceTests)


class TestDecisionOrchestrationServiceValidationsThink(DecisionOrchestrationServiceTests):
    def test_should_raise_validation_exception_on_think_if_context_is_null_and_log_it(
        self) -> None:

        # given
        null_context = None

        null_agent_context_exception = NullAgentContextException(
            message="Agent context is null.")

        expected_exception = DecisionOrchestrationValidationException(
            message="Decision orchestration validation error occurred, "
                + "fix the errors and try again.",
            inner_exception=null_agent_context_exception)

        # when
        with pytest.raises(DecisionOrchestrationValidationException) as actual_exception:
            asyncio.run(self.decision_orchestration_service.think(null_context))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
        assert self.gate_service_mock.mock_calls == []
        assert self.brain_service_mock.mock_calls == []
        assert self.judge_service_mock.mock_calls == []
