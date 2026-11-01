# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.orchestrations.direction.exceptions import (
    DirectionOrchestrationValidationException,
    NullAgentContextException)
from tests.unit.services.orchestrations.direction.direction_orchestration_service_tests import (
    DirectionOrchestrationServiceTests)


class TestDirectionOrchestrationServiceValidationsAct(DirectionOrchestrationServiceTests):
    def test_should_raise_validation_exception_on_act_if_context_is_null_and_log_it(
        self) -> None:

        # given
        null_context = None

        null_agent_context_exception = NullAgentContextException(
            message="Agent context is null.")

        expected_exception = DirectionOrchestrationValidationException(
            message="Direction orchestration validation error occurred, "
                + "fix the errors and try again.",
            inner_exception=null_agent_context_exception)

        # when
        with pytest.raises(DirectionOrchestrationValidationException) as actual_exception:
            asyncio.run(self.direction_orchestration_service.act(null_context))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        self.assert_logged_once("log_error", expected_exception)
        assert self.internal_tool_service_mock.mock_calls == []
        assert self.return_service_mock.mock_calls == []
