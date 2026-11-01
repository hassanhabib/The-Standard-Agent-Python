# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import copy
import dataclasses
from unittest.mock import call

import pytest

from standard_agents.models.foundations.judges.judgement import Judgement
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from tests.unit.services.orchestrations.decision.decision_orchestration_service_tests import (
    DecisionOrchestrationServiceTests)


class TestDecisionOrchestrationServiceLogicThink(DecisionOrchestrationServiceTests):
    def test_should_think_and_decide_to_act(self) -> None:
        # given
        input_context = self.create_random_context()
        random_tool_name = self.create_random_string()
        random_tool_input = self.create_random_string() + ": " + self.create_random_string()
        random_narration = self.create_random_string()
        expected_user_message = self.create_user_message(input_context)

        returned_reply = (
            f"SAY: {random_narration}\n"
            + f"ACTION: {random_tool_name}: {random_tool_input}\n")

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            direction_type=random_tool_name,
            payload=random_tool_input,
            narration=random_narration,
            raw_reply=returned_reply.strip())

        self.gate_service_mock.screen.return_value = "allow"
        self.brain_service_mock.generate.return_value = returned_reply

        # when
        actual_context = asyncio.run(self.decision_orchestration_service.think(input_context))

        # then
        assert actual_context == expected_context
        assert self.gate_service_mock.mock_calls == [call.screen(input_context.prompt)]

        assert self.brain_service_mock.mock_calls == [
            call.generate(input_context.system_prompt, expected_user_message)
        ]

        assert self.judge_service_mock.mock_calls == []

    def test_should_think_and_answer_when_judge_accepts(self) -> None:
        # given
        input_context = self.create_random_context()
        random_answer = self.create_random_string() + "\n" + self.create_random_string()
        expected_user_message = self.create_user_message(input_context)
        returned_reply = f"FINAL: {random_answer}"
        returned_judgement = Judgement(score=0.3, reason=self.create_random_string())

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            direction_type="ReturnResponse",
            payload=random_answer,
            raw_reply=returned_reply)

        self.gate_service_mock.screen.return_value = "allow"
        self.brain_service_mock.generate.return_value = returned_reply
        self.judge_service_mock.evaluate.return_value = returned_judgement

        # when
        actual_context = asyncio.run(self.decision_orchestration_service.think(input_context))

        # then
        assert actual_context == expected_context
        assert self.gate_service_mock.mock_calls == [call.screen(input_context.prompt)]

        assert self.brain_service_mock.mock_calls == [
            call.generate(input_context.system_prompt, expected_user_message)
        ]

        assert self.judge_service_mock.mock_calls == [
            call.evaluate(input_context.prompt, random_answer)
        ]

    def test_should_think_and_revise_when_judge_rejects(self) -> None:
        # given
        input_context = self.create_random_context()
        random_answer = self.create_random_string()
        random_reason = self.create_random_string()
        returned_reply = f"FINAL: {random_answer}"
        returned_judgement = Judgement(score=0.29, reason=random_reason)

        expected_feedback = (
            f"A previous draft was rejected on review: {random_reason}. "
            + f"The draft was: {random_answer}")

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            observations=input_context.observations + (expected_feedback,),
            status=AgentStatus.REVISING)

        self.gate_service_mock.screen.return_value = "allow"
        self.brain_service_mock.generate.return_value = returned_reply
        self.judge_service_mock.evaluate.return_value = returned_judgement

        # when
        actual_context = asyncio.run(self.decision_orchestration_service.think(input_context))

        # then
        assert actual_context == expected_context

        assert self.judge_service_mock.mock_calls == [
            call.evaluate(input_context.prompt, random_answer)
        ]

    @pytest.mark.parametrize("refusing_verdict", ["refuse", "Refuse: unsafe request"])
    def test_should_think_and_refuse_when_gate_refuses(self, refusing_verdict: str) -> None:
        # given
        input_context = self.create_random_context()

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            direction_type="Refuse",
            payload="I'm not able to help with that.")

        self.gate_service_mock.screen.return_value = refusing_verdict

        # when
        actual_context = asyncio.run(self.decision_orchestration_service.think(input_context))

        # then
        assert actual_context == expected_context
        assert self.gate_service_mock.mock_calls == [call.screen(input_context.prompt)]
        assert self.brain_service_mock.mock_calls == []
        assert self.judge_service_mock.mock_calls == []
