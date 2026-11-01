# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import copy
import dataclasses
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

    # SPEC.md 5: a turn that leaves the run working (a tool ran, or a draft went back for
    # revision) hands its context to the next turn's Recall, and the run ends on the first turn
    # whose status is anything else.
    def test_should_run_turn_after_turn_until_a_turn_ends_the_run(self) -> None:
        # given
        input_prompt = self.create_random_string()
        initial_context = AgentContext(prompt=input_prompt)
        first_recalled_context = self.create_random_context(input_prompt)
        first_decided_context = self.create_random_context(input_prompt)
        first_acted_context = self.create_random_context(input_prompt, AgentStatus.WORKING)
        second_recalled_context = self.create_random_context(input_prompt)
        second_decided_context = self.create_random_context(input_prompt)
        second_acted_context = self.create_random_context(input_prompt, AgentStatus.RESPONDED)

        expected_outcome = AgentOutcome(
            result=second_acted_context.result,
            status=AgentStatus.RESPONDED)

        self.data_orchestration_service_mock.recall.side_effect = [
            first_recalled_context,
            second_recalled_context
        ]

        self.decision_orchestration_service_mock.think.side_effect = [
            first_decided_context,
            second_decided_context
        ]

        self.direction_orchestration_service_mock.act.side_effect = [
            first_acted_context,
            second_acted_context
        ]

        # when
        actual_outcome = asyncio.run(self.run_coordination_service.run(input_prompt))

        # then
        assert actual_outcome == expected_outcome

        assert self.data_orchestration_service_mock.mock_calls == [
            call.recall(initial_context),
            call.recall(first_acted_context)
        ]

        assert self.decision_orchestration_service_mock.mock_calls == [
            call.think(first_recalled_context),
            call.think(second_recalled_context)
        ]

        assert self.direction_orchestration_service_mock.mock_calls == [
            call.act(first_decided_context),
            call.act(second_decided_context)
        ]

    # A run that is still working when its turns run out delivers nothing. Saying so is the
    # honest outcome; handing back whatever the last tool returned as if it were an answer is not.
    def test_should_run_out_of_turns_and_fail_without_an_answer(self) -> None:
        # given
        input_prompt = self.create_random_string()
        initial_context = AgentContext(prompt=input_prompt)
        recalled_context = self.create_random_context(input_prompt)
        decided_context = self.create_random_context(input_prompt)
        acted_context = self.create_random_context(input_prompt, AgentStatus.WORKING)
        run_coordination_service = self.create_run_coordination_service(max_turns=1)

        expected_outcome = AgentOutcome(
            result="I ran out of turns before an answer was ready; nothing was delivered.",
            status=AgentStatus.FAILED)

        self.data_orchestration_service_mock.recall.return_value = recalled_context
        self.decision_orchestration_service_mock.think.return_value = decided_context
        self.direction_orchestration_service_mock.act.return_value = acted_context

        # when
        actual_outcome = asyncio.run(run_coordination_service.run(input_prompt))

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

    # SPEC.md 4.4: each invocation establishes its own run identity, and every turn it records is
    # attributed to that run and no other, so two runs on one instance never share a record.
    def test_should_attribute_every_turn_to_its_own_run(self) -> None:
        # given
        input_prompt = self.create_random_string()
        working_context = self.create_random_context(input_prompt, AgentStatus.WORKING)
        responded_context = self.create_random_context(input_prompt, AgentStatus.RESPONDED)
        self.data_orchestration_service_mock.recall.return_value = working_context
        self.decision_orchestration_service_mock.think.return_value = working_context

        self.direction_orchestration_service_mock.act.side_effect = [
            working_context,
            responded_context,
            responded_context
        ]

        # when
        asyncio.run(self.run_coordination_service.run(input_prompt))
        asyncio.run(self.run_coordination_service.run(input_prompt))

        # then
        turn_calls = [
            logged_call for logged_call in self.logging_broker_mock.mock_calls
            if logged_call[0] == "log_turn"
        ]

        run_ids = [logged_call[1][0] for logged_call in turn_calls]
        turns = [logged_call[1][1] for logged_call in turn_calls]

        assert turns == [0, 1, 0]
        assert run_ids[0] == run_ids[1]
        assert run_ids[2] != run_ids[0]
        assert all(run_id != "" for run_id in run_ids)
