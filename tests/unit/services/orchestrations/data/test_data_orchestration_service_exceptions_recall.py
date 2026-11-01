# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from xeptions import Xeption
from standard_agents.models.foundations.knowledges.exceptions import (
    KnowledgeDependencyException,
    KnowledgeServiceException,
    KnowledgeValidationException)
from standard_agents.models.foundations.memories.exceptions import (
    MemoryDependencyException,
    MemoryServiceException)
from standard_agents.models.foundations.skills.exceptions import (
    SkillDependencyException,
    SkillServiceException)
from standard_agents.models.orchestrations.data.exceptions import (
    DataOrchestrationDependencyException,
    DataOrchestrationDependencyValidationException,
    DataOrchestrationServiceException,
    FailedDataOrchestrationServiceException)
from tests.unit.services.orchestrations.data.data_orchestration_service_tests import (
    DataOrchestrationServiceTests)


class TestDataOrchestrationServiceExceptionsRecall(DataOrchestrationServiceTests):
    @pytest.mark.parametrize("dependency_validation_exception_type", [
        KnowledgeValidationException
    ])
    def test_should_raise_dependency_validation_exception_on_recall_if_dependency_validation_error_occurs_and_log_it(
        self,
        dependency_validation_exception_type: type) -> None:

        # given
        input_context = self.create_random_context()
        some_inner_exception = Xeption(message=self.create_random_string())

        dependency_validation_exception = dependency_validation_exception_type(
            message=self.create_random_string(),
            inner_exception=some_inner_exception)

        expected_dependency_validation_exception = DataOrchestrationDependencyValidationException(
            message="Data orchestration dependency validation error occurred, "
                + "fix the errors and try again.",
            inner_exception=some_inner_exception)

        self.skill_service_mock.retrieve_skills.return_value = self.create_random_string()
        self.memory_service_mock.retrieve_all_memories.return_value = []

        self.knowledge_service_mock.retrieve_knowledge.side_effect = (
            dependency_validation_exception)

        # when
        with pytest.raises(DataOrchestrationDependencyValidationException) as actual_exception:
            asyncio.run(self.data_orchestration_service.recall(input_context))

        # then
        assert expected_dependency_validation_exception.same_exception_as(
            actual_exception.value)

        self.assert_logged_once("log_error", expected_dependency_validation_exception)

    @pytest.mark.parametrize("dependency_exception_type", [
        SkillDependencyException,
        SkillServiceException,
        MemoryDependencyException,
        MemoryServiceException,
        KnowledgeDependencyException,
        KnowledgeServiceException
    ])
    def test_should_raise_dependency_exception_on_recall_if_dependency_error_occurs_and_log_it(
        self,
        dependency_exception_type: type) -> None:

        # given
        input_context = self.create_random_context()
        some_inner_exception = Xeption(message=self.create_random_string())

        dependency_exception = dependency_exception_type(
            message=self.create_random_string(),
            inner_exception=some_inner_exception)

        expected_dependency_exception = DataOrchestrationDependencyException(
            message="Data orchestration dependency error occurred, contact support.",
            inner_exception=some_inner_exception)

        self.skill_service_mock.retrieve_skills.side_effect = dependency_exception

        # when
        with pytest.raises(DataOrchestrationDependencyException) as actual_exception:
            asyncio.run(self.data_orchestration_service.recall(input_context))

        # then
        assert expected_dependency_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_dependency_exception)
        assert self.memory_service_mock.mock_calls == []
        assert self.knowledge_service_mock.mock_calls == []

    def test_should_raise_service_exception_on_recall_if_service_error_occurs_and_log_it(
        self) -> None:

        # given
        input_context = self.create_random_context()
        service_error = Exception(self.create_random_string())

        failed_data_orchestration_service_exception = FailedDataOrchestrationServiceException(
            message="Failed data orchestration service error occurred, contact support.",
            inner_exception=service_error)

        expected_data_orchestration_service_exception = DataOrchestrationServiceException(
            message="Data orchestration service error occurred, contact support.",
            inner_exception=failed_data_orchestration_service_exception)

        self.skill_service_mock.retrieve_skills.side_effect = service_error

        # when
        with pytest.raises(DataOrchestrationServiceException) as actual_exception:
            asyncio.run(self.data_orchestration_service.recall(input_context))

        # then
        assert expected_data_orchestration_service_exception.same_exception_as(
            actual_exception.value)

        self.assert_logged_once("log_error", expected_data_orchestration_service_exception)
