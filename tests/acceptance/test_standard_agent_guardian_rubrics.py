# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import uuid
from pathlib import Path

from standard_agents.standard_agent import StandardAgent


# SPEC.md 4.5: a guardian's rubric is assembled, not hardcoded, from up to three ordered layers:
# an optional constitution, a policy (built in, or replaced by a consumption skill), and the
# framework-owned contract that is always present and never replaceable.
def create_random_string() -> str:
    return uuid.uuid4().hex


class GuardianRecorder:
    def __init__(self) -> None:
        self.gate_rubrics: list[str] = []
        self.judge_rubrics: list[str] = []

    async def gate(self, rubric: str, text: str) -> str:
        self.gate_rubrics.append(rubric)

        return "accept"

    async def judge(self, rubric: str, task: str, candidate: str) -> str:
        self.judge_rubrics.append(rubric)

        return "SCORE: 1.0\nREASON: ok"

    def compose(self) -> StandardAgent:
        async def brain(system_prompt: str, user_prompt: str) -> str:
            return "FINAL: done"

        return StandardAgent().on_gate(self.gate).on_judge(self.judge).on_brain(brain)


class TestStandardAgentGuardianRubrics:
    def test_should_hand_each_guardian_its_policy_then_its_contract(self) -> None:
        # given
        guardians = GuardianRecorder()
        agent = guardians.compose()

        # when
        asyncio.run(agent.run(create_random_string()))

        # then
        gate_rubric = guardians.gate_rubrics[0]
        judge_rubric = guardians.judge_rubrics[0]
        assert gate_rubric.startswith("You are the Gate")
        assert judge_rubric.startswith("You are the Judge")
        assert gate_rubric.index("You are not the Brain.") < gate_rubric.index("Reply with exactly")
        assert judge_rubric.index("You are not the Brain.") < judge_rubric.index("Reply with exactly")

    def test_should_put_a_constitution_above_both_guardians(self, tmp_path: Path) -> None:
        # given
        constitution = "CONSTITUTION: " + create_random_string()
        constitution_file = tmp_path.joinpath("constitution.md")
        constitution_file.write_text(constitution, encoding="utf-8")
        guardians = GuardianRecorder()
        agent = guardians.compose().constitution(str(constitution_file))

        # when
        asyncio.run(agent.run(create_random_string()))

        # then
        for rubric in guardians.gate_rubrics + guardians.judge_rubrics:
            assert rubric.startswith(constitution)
            assert "You are not the Brain." in rubric
            assert "Reply with exactly" in rubric

    def test_should_let_a_consumption_skill_replace_the_policy_but_never_the_contract(
        self,
        tmp_path: Path) -> None:

        # given
        consumption = "CONSUMPTION POLICY: " + create_random_string()
        consumption_file = tmp_path.joinpath("consumption.md")
        consumption_file.write_text(consumption, encoding="utf-8")
        guardians = GuardianRecorder()
        agent = guardians.compose().consumption(str(consumption_file))

        # when
        asyncio.run(agent.run(create_random_string()))

        # then
        for rubric in guardians.gate_rubrics + guardians.judge_rubrics:
            assert rubric.startswith(consumption)
            assert "You are not the Brain." not in rubric
            assert "Reply with exactly" in rubric
