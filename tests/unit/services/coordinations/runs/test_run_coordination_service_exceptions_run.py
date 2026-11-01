# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from xeptions import Xeption
from standard_agents.models.coordinations.runs.exceptions import (
    FailedRunCoordinationServiceException,
    RunCoordinationDependencyException,
    RunCoordinationDependencyValidationException,
    RunCoordinationServiceException)
from standard_agents.models.orchestrations.data.exceptions import (
    DataOrchestrationDependencyException,
    DataOrchestrationDependencyValidationException,
    DataOrchestrationServiceException,
    DataOrchestrationValidationException)
from standard_agents.models.orchestrations.decision.exceptions import (
    DecisionOrchestrationDependencyException,
    DecisionOrchestrationDependencyValidationException,
    DecisionOrchestrationServiceException,
    DecisionOrchestrationValidationException)
from standard_agents.models.orchestrations.direction.exceptions import (
    DirectionOrchestrationDependencyException,
    DirectionOrchestrationDependencyValidationException,
    DirectionOrchestrationServiceException,
    DirectionOrchestrationValidationException)
from tests.unit.services.coordinations.runs.run_coordination_service_tests import (
    RunCoordinationServiceTests)


class TestRunCoordinationServiceExceptionsRun(RunCoordinationServiceTests):
    # Above the orchestrations, a nature's validation and dependency validation are both a
    # dependency validation of the run: the local exception is kept, the category is the run's.
    @pytest.mark.parametrize("dependency_validation_exception_type", [
        DataOrchestrationValidationException,
        DataOrchestrationDependencyValidationException,
        DecisionOrchestrationValidationException,
        DecisionOrchestrationDependencyValidationException,
        DirectionOrchestrationValidationException,
        DirectionOrchestrationDependencyValidationException
    ])
    def test_should_raise_dependency_validation_exception_on_run_if_dependency_validation_error_occurs_and_log_it(
        self,
        dependency_validation_exception_type: type) -> None:

        # given
        input_prompt = self.create_random_string()
        some_inner_exception = Xeption(message=self.create_random_string())

        dependency_validation_exception = dependency_validation_exception_type(
            message=self.create_random_string(),
            inner_exception=some_inner_exception)

        expected_exception = RunCoordinationDependencyValidationException(
            message="Run coordination dependency validation error occurred, "
                + "fix the errors and try again.",
            inner_exception=some_inner_exception)

        self.data_orchestration_service_mock.recall.side_effect = dependency_validation_exception

        # when
        with pytest.raises(RunCoordinationDependencyValidationException) as actual_exception:
            asyncio.run(self.run_coordination_service.run(input_prompt))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
        assert self.decision_orchestration_service_mock.mock_calls == []
        assert self.direction_orchestration_service_mock.mock_calls == []

    @pytest.mark.parametrize("dependency_exception_type", [
        DataOrchestrationDependencyException,
        DataOrchestrationServiceException,
        DecisionOrchestrationDependencyException,
        DecisionOrchestrationServiceException,
        DirectionOrchestrationDependencyException,
        DirectionOrchestrationServiceException
    ])
    def test_should_raise_dependency_exception_on_run_if_dependency_error_occurs_and_log_it(
        self,
        dependency_exception_type: type) -> None:

        # given
        input_prompt = self.create_random_string()
        some_inner_exception = Xeption(message=self.create_random_string())

        dependency_exception = dependency_exception_type(
            message=self.create_random_string(),
            inner_exception=some_inner_exception)

        expected_exception = RunCoordinationDependencyException(
            message="Run coordination dependency error occurred, contact support.",
            inner_exception=some_inner_exception)

        self.data_orchestration_service_mock.recall.side_effect = dependency_exception

        # when
        with pytest.raises(RunCoordinationDependencyException) as actual_exception:
            asyncio.run(self.run_coordination_service.run(input_prompt))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
        assert self.decision_orchestration_service_mock.mock_calls == []
        assert self.direction_orchestration_service_mock.mock_calls == []

    def test_should_raise_service_exception_on_run_if_service_error_occurs_and_log_it(
        self) -> None:

        # given
        input_prompt = self.create_random_string()
        service_error = Exception(self.create_random_string())

        failed_service_exception = FailedRunCoordinationServiceException(
            message="Failed run coordination service error occurred, contact support.",
            inner_exception=service_error)

        expected_exception = RunCoordinationServiceException(
            message="Run coordination service error occurred, contact support.",
            inner_exception=failed_service_exception)

        self.data_orchestration_service_mock.recall.side_effect = service_error

        # when
        with pytest.raises(RunCoordinationServiceException) as actual_exception:
            asyncio.run(self.run_coordination_service.run(input_prompt))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
