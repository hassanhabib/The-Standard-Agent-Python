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

    # SPEC.md 4.3: an act on a tool the agent does not own goes out across the boundary, and what
    # comes back is an observation like any tool's, with the run still working.
    def test_should_act_by_calling_out_for_a_tool_the_agent_does_not_own(self) -> None:
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

        self.internal_tool_service_mock.handles.return_value = False
        self.external_tool_service_mock.call.return_value = returned_outcome

        # when
        actual_context = asyncio.run(self.direction_orchestration_service.act(input_context))

        # then
        assert actual_context == expected_context

        assert self.internal_tool_service_mock.mock_calls == [
            call.handles(random_tool_name)
        ]

        assert self.external_tool_service_mock.mock_calls == [
            call.call(random_tool_name, input_context.payload)
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
