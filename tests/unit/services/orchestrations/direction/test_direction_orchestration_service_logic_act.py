# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import copy
import dataclasses
from unittest.mock import call

import pytest

from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from tests.unit.services.orchestrations.direction.direction_orchestration_service_tests import (
    DirectionOrchestrationServiceTests)


class TestDirectionOrchestrationServiceLogicAct(DirectionOrchestrationServiceTests):
    @pytest.mark.parametrize("terminal_direction, expected_status", [
        ("ReturnResponse", AgentStatus.RESPONDED),
        ("Refuse", AgentStatus.REFUSED),
        ("AwaitInput", AgentStatus.AWAITING_INPUT)
    ])
    def test_should_act_by_returning_on_terminal_direction(
        self,
        terminal_direction: str,
        expected_status: AgentStatus) -> None:

        # given
        input_context = self.create_random_context(terminal_direction)
        returned_result = self.create_random_string()

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            result=returned_result,
            status=expected_status)

        self.return_service_mock.return_payload.return_value = returned_result

        # when
        actual_context = asyncio.run(self.direction_orchestration_service.act(input_context))

        # then
        assert actual_context == expected_context

        assert self.return_service_mock.mock_calls == [
            call.return_payload(input_context.payload)
        ]

        assert self.internal_tool_service_mock.mock_calls == []
