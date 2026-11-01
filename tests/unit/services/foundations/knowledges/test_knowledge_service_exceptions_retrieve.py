# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.knowledges.exceptions import (
    FailedKnowledgeDependencyException,
    FailedKnowledgeServiceException,
    KnowledgeDependencyException,
    KnowledgeServiceException)
from tests.unit.services.foundations.knowledges.knowledge_service_tests import (
    KnowledgeServiceTests)


class TestKnowledgeServiceExceptionsRetrieve(KnowledgeServiceTests):
    def test_should_raise_dependency_exception_on_retrieve_if_os_error_occurs_and_log_it(
        self) -> None:

        # given
        input_query = self.create_random_string()
        os_error = ConnectionError(self.create_random_string())

        failed_knowledge_dependency_exception = FailedKnowledgeDependencyException(
            message="Failed knowledge dependency error occurred, contact support.",
            inner_exception=os_error)

        expected_knowledge_dependency_exception = KnowledgeDependencyException(
            message="Knowledge dependency error occurred, contact support.",
            inner_exception=failed_knowledge_dependency_exception)

        self.knowledge_broker_mock.select_knowledge.side_effect = os_error

        # when
        with pytest.raises(KnowledgeDependencyException) as actual_knowledge_dependency_exception:
            asyncio.run(self.knowledge_service.retrieve_knowledge(input_query))

        # then
        assert expected_knowledge_dependency_exception.same_exception_as(
            actual_knowledge_dependency_exception.value)

        assert self.knowledge_broker_mock.mock_calls == [call.select_knowledge(input_query)]
        self.assert_logged_once("log_error", expected_knowledge_dependency_exception)

    def test_should_raise_service_exception_on_retrieve_if_service_error_occurs_and_log_it(
        self) -> None:

        # given
        input_query = self.create_random_string()
        service_error = Exception(self.create_random_string())

        failed_knowledge_service_exception = FailedKnowledgeServiceException(
            message="Failed knowledge service error occurred, contact support.",
            inner_exception=service_error)

        expected_knowledge_service_exception = KnowledgeServiceException(
            message="Knowledge service error occurred, contact support.",
            inner_exception=failed_knowledge_service_exception)

        self.knowledge_broker_mock.select_knowledge.side_effect = service_error

        # when
        with pytest.raises(KnowledgeServiceException) as actual_knowledge_service_exception:
            asyncio.run(self.knowledge_service.retrieve_knowledge(input_query))

        # then
        assert expected_knowledge_service_exception.same_exception_as(
            actual_knowledge_service_exception.value)

        assert self.knowledge_broker_mock.mock_calls == [call.select_knowledge(input_query)]
        self.assert_logged_once("log_error", expected_knowledge_service_exception)
