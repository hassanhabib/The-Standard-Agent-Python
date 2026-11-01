# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.orchestrations.data.exceptions import (
    DataOrchestrationValidationException,
    NullAgentContextException)
from tests.unit.services.orchestrations.data.data_orchestration_service_tests import (
    DataOrchestrationServiceTests)


class TestDataOrchestrationServiceValidationsRecall(DataOrchestrationServiceTests):
    def test_should_raise_validation_exception_on_recall_if_context_is_null_and_log_it(
        self) -> None:

        # given
        null_context = None

        null_agent_context_exception = NullAgentContextException(
            message="Agent context is null.")

        expected_data_orchestration_validation_exception = DataOrchestrationValidationException(
            message="Data orchestration validation error occurred, fix the errors and try again.",
            inner_exception=null_agent_context_exception)

        # when
        with pytest.raises(DataOrchestrationValidationException) as actual_exception:
            asyncio.run(self.data_orchestration_service.recall(null_context))

        # then
        assert expected_data_orchestration_validation_exception.same_exception_as(
            actual_exception.value)

        self.assert_logged_once("log_error", expected_data_orchestration_validation_exception)
        assert self.skill_service_mock.mock_calls == []
        assert self.memory_service_mock.mock_calls == []
        assert self.knowledge_service_mock.mock_calls == []
