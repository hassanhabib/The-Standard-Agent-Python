# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import uuid

from standard_agents.brokers.classifiers.iclassifier_broker import IClassifierBroker
from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.brokers.knowledges.iknowledge_broker import IKnowledgeBroker
from standard_agents.brokers.memories.imemory_broker import IMemoryBroker
from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker
from standard_agents.standard_agent import StandardAgent


# Every capability is reachable three ways: Local (a path), Custom (on_*, your own function) and
# External (use_*, a provider's broker). These tests compose the agent the External way and the
# Custom way and prove each broker is the one the agent consults.
def create_random_string() -> str:
    return uuid.uuid4().hex


class RecordingBrain(IGeneratorBroker):
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))

        return f"FINAL: {self.answer}"


class StaticSkills(ISkillBroker):
    def __init__(self, skills: dict[str, str]) -> None:
        self.skills = skills

    async def select_skill_names(self) -> list[str]:
        return list(self.skills)

    async def select_skill_content(self, skill_name: str) -> str:
        return self.skills[skill_name]


class StaticMemories(IMemoryBroker):
    def __init__(self, memories: list[str]) -> None:
        self.memories = memories

    async def select_all_memories(self) -> list[str]:
        return self.memories


class StaticKnowledge(IKnowledgeBroker):
    def __init__(self, knowledge: list[str]) -> None:
        self.knowledge = knowledge

    async def select_knowledge(self, query: str) -> list[str]:
        return self.knowledge


class AllowingGate(IClassifierBroker):
    def __init__(self) -> None:
        self.screened: list[str] = []

    async def classify(self, text: str) -> str:
        self.screened.append(text)

        return "allow"


class AcceptingJudge(IVerifierBroker):
    def __init__(self) -> None:
        self.reviewed: list[str] = []

    async def verify(self, task: str, candidate: str) -> str:
        self.reviewed.append(candidate)

        return "1.0"


class TestStandardAgentCompositions:
    def test_should_compose_from_brokers_the_host_supplies(self) -> None:
        # given
        input_prompt = create_random_string()
        random_answer = create_random_string()
        random_skill = create_random_string()
        random_memory = create_random_string()
        random_knowledge = create_random_string()
        brain = RecordingBrain(random_answer)
        gate = AllowingGate()
        judge = AcceptingJudge()

        agent = (StandardAgent()
            .use_generator(brain)
            .use_skills(StaticSkills({"skill.md": random_skill}))
            .use_memory(StaticMemories([random_memory]))
            .use_knowledge(StaticKnowledge([random_knowledge]))
            .use_gate(gate)
            .use_judge(judge))

        # when
        actual_answer = asyncio.run(agent.process_prompt(input_prompt))

        # then
        assert actual_answer == random_answer
        assert brain.calls[0][0] == random_skill
        assert random_memory in brain.calls[0][1]
        assert random_knowledge in brain.calls[0][1]
        assert gate.screened == [input_prompt]
        assert judge.reviewed == [random_answer]
