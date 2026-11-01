# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from tests.unit.services.coordinations.runs.run_coordination_service_tests import (
    RunCoordinationServiceTests)


class TestRunCoordinationServiceLogicRun(RunCoordinationServiceTests):
    @pytest.mark.parametrize("terminal_status", [
        AgentStatus.RESPONDED,
        AgentStatus.REFUSED,
        AgentStatus.AWAITING_INPUT
    ])
    def test_should_run_and_end_in_one_turn(self, terminal_status: AgentStatus) -> None:
        # given
        input_prompt = self.create_random_string()
        initial_context = AgentContext(prompt=input_prompt)
        recalled_context = self.create_random_context(input_prompt)
        decided_context = self.create_random_context(input_prompt)
        acted_context = self.create_random_context(input_prompt, terminal_status)
        expected_outcome = AgentOutcome(result=acted_context.result, status=terminal_status)
        self.data_orchestration_service_mock.recall.return_value = recalled_context
        self.decision_orchestration_service_mock.think.return_value = decided_context
        self.direction_orchestration_service_mock.act.return_value = acted_context

        # when
        actual_outcome = asyncio.run(self.run_coordination_service.run(input_prompt))

        # then
        assert actual_outcome == expected_outcome

        assert self.data_orchestration_service_mock.mock_calls == [
            call.recall(initial_context)
        ]

        assert self.decision_orchestration_service_mock.mock_calls == [
            call.think(recalled_context)
        ]

        assert self.direction_orchestration_service_mock.mock_calls == [
            call.act(decided_context)
        ]
