# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from xeptions import Xeption
from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyException,
    ExternalToolServiceException,
    ExternalToolValidationException)
from standard_agents.models.foundations.internal_tools.exceptions import (
    InternalToolDependencyException,
    InternalToolServiceException,
    InternalToolValidationException)
from standard_agents.models.foundations.returns.exceptions import ReturnValidationException
from standard_agents.models.orchestrations.direction.exceptions import (
    DirectionOrchestrationDependencyException,
    DirectionOrchestrationDependencyValidationException,
    DirectionOrchestrationServiceException,
    FailedDirectionOrchestrationServiceException)
from tests.unit.services.orchestrations.direction.direction_orchestration_service_tests import (
    DirectionOrchestrationServiceTests)


class TestDirectionOrchestrationServiceExceptionsAct(DirectionOrchestrationServiceTests):
    @pytest.mark.parametrize("dependency_validation_exception_type", [
        InternalToolValidationException,
        ExternalToolValidationException,
        ReturnValidationException
    ])
    def test_should_raise_dependency_validation_exception_on_act_if_dependency_validation_error_occurs_and_log_it(
        self,
        dependency_validation_exception_type: type) -> None:

        # given
        input_context = self.create_random_context(self.create_random_string())
        some_inner_exception = Xeption(message=self.create_random_string())

        dependency_validation_exception = dependency_validation_exception_type(
            message=self.create_random_string(),
            inner_exception=some_inner_exception)

        expected_exception = DirectionOrchestrationDependencyValidationException(
            message="Direction orchestration dependency validation error occurred, "
                + "fix the errors and try again.",
            inner_exception=some_inner_exception)

        self.internal_tool_service_mock.handles.side_effect = dependency_validation_exception

        # when
        with pytest.raises(DirectionOrchestrationDependencyValidationException) as actual_exception:
            asyncio.run(self.direction_orchestration_service.act(input_context))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
        assert self.return_service_mock.mock_calls == []

    @pytest.mark.parametrize("dependency_exception_type", [
        InternalToolDependencyException,
        InternalToolServiceException,
        ExternalToolDependencyException,
        ExternalToolServiceException
    ])
    def test_should_raise_dependency_exception_on_act_if_dependency_error_occurs_and_log_it(
        self,
        dependency_exception_type: type) -> None:

        # given
        input_context = self.create_random_context(self.create_random_string())
        some_inner_exception = Xeption(message=self.create_random_string())

        dependency_exception = dependency_exception_type(
            message=self.create_random_string(),
            inner_exception=some_inner_exception)

        expected_exception = DirectionOrchestrationDependencyException(
            message="Direction orchestration dependency error occurred, contact support.",
            inner_exception=some_inner_exception)

        self.internal_tool_service_mock.handles.side_effect = dependency_exception

        # when
        with pytest.raises(DirectionOrchestrationDependencyException) as actual_exception:
            asyncio.run(self.direction_orchestration_service.act(input_context))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
        assert self.return_service_mock.mock_calls == []

    def test_should_raise_service_exception_on_act_if_service_error_occurs_and_log_it(
        self) -> None:

        # given
        input_context = self.create_random_context(self.create_random_string())
        service_error = Exception(self.create_random_string())

        failed_service_exception = FailedDirectionOrchestrationServiceException(
            message="Failed direction orchestration service error occurred, contact support.",
            inner_exception=service_error)

        expected_exception = DirectionOrchestrationServiceException(
            message="Direction orchestration service error occurred, contact support.",
            inner_exception=failed_service_exception)

        self.internal_tool_service_mock.handles.side_effect = service_error

        # when
        with pytest.raises(DirectionOrchestrationServiceException) as actual_exception:
            asyncio.run(self.direction_orchestration_service.act(input_context))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
