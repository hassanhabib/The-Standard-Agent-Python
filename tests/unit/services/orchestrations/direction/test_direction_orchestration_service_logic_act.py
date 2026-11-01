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

    def test_should_act_by_running_tool_and_observing_its_outcome(self) -> None:
        # given
        random_tool_name = self.create_random_string()
        input_context = self.create_random_context(random_tool_name)
        returned_outcome = self.create_random_string()

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            observations=input_context.observations + (
                f"{random_tool_name} returned: {returned_outcome}",),
            result=returned_outcome,
            status=AgentStatus.WORKING)

        self.internal_tool_service_mock.handles.return_value = True
        self.internal_tool_service_mock.run.return_value = returned_outcome

        # when
        actual_context = asyncio.run(self.direction_orchestration_service.act(input_context))

        # then
        assert actual_context == expected_context

        assert self.internal_tool_service_mock.mock_calls == [
            call.handles(random_tool_name),
            call.run(random_tool_name, input_context.payload)
        ]

        assert self.return_service_mock.mock_calls == []

    # A brain that names a tool the agent does not have is told so, and the run goes on: the next
    # turn can pick a real tool or answer. Acting on a name nobody registered never happens.
    def test_should_act_by_observing_that_an_unknown_tool_is_not_available(self) -> None:
        # given
        random_tool_name = self.create_random_string()
        input_context = self.create_random_context(random_tool_name)

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            observations=input_context.observations + (
                f"There is no tool named '{random_tool_name}'. "
                + "Use a tool from the catalog, or give a FINAL answer.",),
            result="",
            status=AgentStatus.WORKING)

        self.internal_tool_service_mock.handles.return_value = False

        # when
        actual_context = asyncio.run(self.direction_orchestration_service.act(input_context))

        # then
        assert actual_context == expected_context

        assert self.internal_tool_service_mock.mock_calls == [
            call.handles(random_tool_name)
        ]

        assert self.return_service_mock.mock_calls == []

    # A turn whose draft the Judge sent back decided nothing; there is nothing to route, so the
    # turn ends as it came, still working, and no foundation is asked anything.
    def test_should_act_on_nothing_when_nothing_was_decided(self) -> None:
        # given
        input_context = self.create_random_context("")
        expected_context = copy.deepcopy(input_context)

        # when
        actual_context = asyncio.run(self.direction_orchestration_service.act(input_context))

        # then
        assert actual_context == expected_context
        assert self.internal_tool_service_mock.mock_calls == []
        assert self.return_service_mock.mock_calls == []
