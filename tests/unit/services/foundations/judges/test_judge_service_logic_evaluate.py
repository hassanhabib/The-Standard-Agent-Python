# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

from standard_agents.models.foundations.judges.judgement import Judgement
from tests.unit.services.foundations.judges.judge_service_tests import JudgeServiceTests


class TestJudgeServiceLogicEvaluate(JudgeServiceTests):
    def test_should_evaluate_into_score_and_reason(self) -> None:
        # given
        input_judge_prompt = self.create_random_string()
        input_task = self.create_random_string()
        input_candidate = self.create_random_string()
        random_score = self.create_random_score()
        random_reason = self.create_random_string() + " " + self.create_random_string()
        returned_verdict = f" {random_score} {random_reason}\n"
        expected_judgement = Judgement(score=random_score, reason=random_reason)
        self.verifier_broker_mock.verify.return_value = returned_verdict

        # when
        actual_judgement = asyncio.run(self.judge_service.evaluate(input_judge_prompt, input_task, input_candidate))

        # then
        assert actual_judgement == expected_judgement

        assert self.verifier_broker_mock.mock_calls == [
            call.verify(input_judge_prompt, input_task, input_candidate)
        ]

        assert self.logging_broker_mock.mock_calls == []

    # The Judge's contract (SPEC.md 4.5) asks for two lines, SCORE: and REASON:, and a reason of
    # "ok" means there is nothing to fix.
    def test_should_evaluate_a_verdict_written_to_the_contract(self) -> None:
        # given
        input_judge_prompt = self.create_random_string()
        input_task = self.create_random_string()
        input_candidate = self.create_random_string()
        random_score = self.create_random_score()
        random_reason = self.create_random_string() + " " + self.create_random_string()
        returned_verdict = f"SCORE: {random_score}\nREASON: {random_reason}\n"
        expected_judgement = Judgement(score=random_score, reason=random_reason)
        self.verifier_broker_mock.verify.return_value = returned_verdict

        # when
        actual_judgement = asyncio.run(
            self.judge_service.evaluate(input_judge_prompt, input_task, input_candidate))

        # then
        assert actual_judgement == expected_judgement
