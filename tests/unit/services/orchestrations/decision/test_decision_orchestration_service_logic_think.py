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
        expected_user_message = self.create_user_message(input_context)
        returned_reply = f"ACTION: {random_tool_name}: {random_tool_input}\n"

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            intent=random_tool_name,
            direction_type=random_tool_name,
            payload=random_tool_input,
            raw_reply=returned_reply.strip())

        self.gate_service_mock.screen.return_value = "allow"
        self.brain_service_mock.generate.return_value = returned_reply

        # when
        actual_context = asyncio.run(self.decision_orchestration_service.think(input_context))

        # then
        assert actual_context == expected_context
        assert self.gate_service_mock.mock_calls == [call.screen(self.gate_rubric, input_context.prompt)]

        assert self.brain_service_mock.mock_calls == [
            call.generate(input_context.system_prompt, expected_user_message)
        ]

        assert self.judge_service_mock.mock_calls == []

    # This implementation does not voice narration, so under SPEC.md 6.0 a SAY: line is the
    # reply's first line under the unamended rules: not an ACTION, so the whole reply is the
    # answer, and no act is taken on a line that was never the first.
    def test_should_think_and_read_a_say_line_as_the_first_line(self) -> None:
        # given
        input_context = self.create_random_context()
        random_tool_name = self.create_random_string()
        returned_reply = f"SAY: {self.create_random_string()}\nACTION: {random_tool_name}: x"
        returned_judgement = Judgement(score=1.0)

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            intent="Respond",
            direction_type="ReturnResponse",
            payload=returned_reply,
            raw_reply=returned_reply)

        self.gate_service_mock.screen.return_value = "allow"
        self.brain_service_mock.generate.return_value = returned_reply
        self.judge_service_mock.evaluate.return_value = returned_judgement

        # when
        actual_context = asyncio.run(self.decision_orchestration_service.think(input_context))

        # then
        assert actual_context == expected_context

    def test_should_think_and_answer_when_judge_accepts(self) -> None:
        # given
        input_context = self.create_random_context()
        random_answer = self.create_random_string() + "\n" + self.create_random_string()
        expected_user_message = self.create_user_message(input_context)
        returned_reply = f"FINAL: {random_answer}"
        returned_judgement = Judgement(score=0.3, reason=self.create_random_string())

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            intent="Respond",
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
        assert self.gate_service_mock.mock_calls == [call.screen(self.gate_rubric, input_context.prompt)]

        assert self.brain_service_mock.mock_calls == [
            call.generate(input_context.system_prompt, expected_user_message)
        ]

        assert self.judge_service_mock.mock_calls == [
            call.evaluate(self.judge_rubric, input_context.prompt, random_answer)
        ]

    # A rejected draft is never delivered, and Decision does not write the status (SPEC.md 3.2:
    # status is Direction's). The turn ends with no decision at all, the stale choice of the last
    # turn cleared, and the Judge's reason in the observations the next attempt reads (4.3).
    def test_should_think_and_decide_nothing_when_judge_rejects(self) -> None:
        # given
        input_context = dataclasses.replace(
            self.create_random_context(),
            direction_type=self.create_random_string(),
            payload=self.create_random_string())

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
            direction_type="",
            payload="",
            raw_reply=returned_reply,
            status=AgentStatus.WORKING)

        self.gate_service_mock.screen.return_value = "allow"
        self.brain_service_mock.generate.return_value = returned_reply
        self.judge_service_mock.evaluate.return_value = returned_judgement

        # when
        actual_context = asyncio.run(self.decision_orchestration_service.think(input_context))

        # then
        assert actual_context == expected_context

        assert self.judge_service_mock.mock_calls == [
            call.evaluate(self.judge_rubric, input_context.prompt, random_answer)
        ]

    @pytest.mark.parametrize("refusing_verdict", ["refuse", "Refuse: unsafe request"])
    def test_should_think_and_refuse_when_gate_refuses(self, refusing_verdict: str) -> None:
        # given
        input_context = self.create_random_context()

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            intent="Refuse",
            direction_type="Refuse",
            payload="I'm not able to help with that.")

        self.gate_service_mock.screen.return_value = refusing_verdict

        # when
        actual_context = asyncio.run(self.decision_orchestration_service.think(input_context))

        # then
        assert actual_context == expected_context
        assert self.gate_service_mock.mock_calls == [call.screen(self.gate_rubric, input_context.prompt)]
        assert self.brain_service_mock.mock_calls == []
        assert self.judge_service_mock.mock_calls == []
