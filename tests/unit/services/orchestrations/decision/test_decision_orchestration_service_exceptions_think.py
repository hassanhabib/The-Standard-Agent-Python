# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from xeptions import Xeption
from standard_agents.models.foundations.brains.exceptions import BrainValidationException
from standard_agents.models.foundations.gates.exceptions import GateValidationException
from standard_agents.models.foundations.judges.exceptions import JudgeValidationException
from standard_agents.models.orchestrations.decision.exceptions import (
    DecisionOrchestrationDependencyValidationException)
from tests.unit.services.orchestrations.decision.decision_orchestration_service_tests import (
    DecisionOrchestrationServiceTests)


class TestDecisionOrchestrationServiceExceptionsThink(DecisionOrchestrationServiceTests):
    @pytest.mark.parametrize("dependency_validation_exception_type", [
        BrainValidationException,
        GateValidationException,
        JudgeValidationException
    ])
    def test_should_raise_dependency_validation_exception_on_think_if_dependency_validation_error_occurs_and_log_it(
        self,
        dependency_validation_exception_type: type) -> None:

        # given
        input_context = self.create_random_context()
        some_inner_exception = Xeption(message=self.create_random_string())

        dependency_validation_exception = dependency_validation_exception_type(
            message=self.create_random_string(),
            inner_exception=some_inner_exception)

        expected_exception = DecisionOrchestrationDependencyValidationException(
            message="Decision orchestration dependency validation error occurred, "
                + "fix the errors and try again.",
            inner_exception=some_inner_exception)

        self.gate_service_mock.screen.side_effect = dependency_validation_exception

        # when
        with pytest.raises(DecisionOrchestrationDependencyValidationException) as actual_exception:
            asyncio.run(self.decision_orchestration_service.think(input_context))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
        assert self.brain_service_mock.mock_calls == []
        assert self.judge_service_mock.mock_calls == []
