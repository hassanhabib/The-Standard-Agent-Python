# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import uuid

from standard_agents.brokers.classifiers.iclassifier_broker import IClassifierBroker
from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.brokers.knowledges.iknowledge_broker import IKnowledgeBroker
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.memories.imemory_broker import IMemoryBroker
from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.itool import ITool


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


class RecordingLoggingBroker(ILoggingBroker):
    def __init__(self) -> None:
        self.turns: list[int] = []

    async def log_information(self, message: str) -> None: ...

    async def log_warning(self, message: str) -> None: ...

    async def log_error(self, exception: BaseException) -> None: ...

    async def log_critical(self, exception: BaseException) -> None: ...

    async def log_turn(self, turn: int) -> None:
        self.turns.append(turn)

    async def log_process(self, actor: str, message: str) -> None: ...


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

    def test_should_trace_through_a_logging_broker_the_host_supplies(self) -> None:
        # given
        input_prompt = create_random_string()
        logging_broker = RecordingLoggingBroker()

        async def brain(system_prompt: str, user_prompt: str) -> str:
            return "FINAL: done"

        agent = StandardAgent().use_logging(logging_broker).on_brain(brain)

        # when
        asyncio.run(agent.run(input_prompt))

        # then
        assert logging_broker.turns == [0]

    def test_should_compose_from_functions_the_host_writes(self) -> None:
        # given
        input_prompt = create_random_string()
        random_skill = create_random_string()
        random_memory = create_random_string()
        first_tool = NamedTool("first")
        second_tool = NamedTool("second")
        brain_calls = []

        async def skills() -> dict[str, str]:
            return {"skill.md": random_skill + "\n{{tools}}"}

        async def memories() -> list[str]:
            return [random_memory]

        async def brain(system_prompt: str, user_prompt: str) -> str:
            brain_calls.append((system_prompt, user_prompt))

            return "FINAL: done"

        expected_system_prompt = (
            f"{random_skill}\n- first: the first tool\n- second: the second tool")

        agent = (StandardAgent()
            .on_skills(skills)
            .on_memory(memories)
            .tools([first_tool, second_tool])
            .on_brain(brain))

        # when
        asyncio.run(agent.run(input_prompt))

        # then
        assert brain_calls[0][0] == expected_system_prompt
        assert random_memory in brain_calls[0][1]


class NamedTool(ITool):
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name

    @property
    def name(self) -> str:
        return self.tool_name

    @property
    def description(self) -> str:
        return f"the {self.tool_name} tool"

    async def execute(self, input: str) -> str:
        return input
