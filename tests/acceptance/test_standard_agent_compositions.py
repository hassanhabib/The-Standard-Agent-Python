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
from standard_agents.brokers.mcps.imcp_broker import IMcpBroker
from standard_agents.brokers.memories.imemory_broker import IMemoryBroker
from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker
from standard_agents.models.brokers.mcps.remote_tool import RemoteTool
from standard_agents.models.foundations.skills.skill import Skill
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
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = skills

    async def select_skills(self) -> list[Skill]:
        return self.skills


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

    async def classify(self, system_prompt: str, text: str) -> str:
        self.screened.append(text)

        return "allow"


class AcceptingJudge(IVerifierBroker):
    def __init__(self) -> None:
        self.reviewed: list[str] = []

    async def verify(self, system_prompt: str, task: str, candidate: str) -> str:
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
            .use_skills(StaticSkills([Skill(name="skill.md", content=random_skill)]))
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

        async def skills() -> list[Skill]:
            return [Skill(name="skill.md", content=random_skill + "\n{{tools}}")]

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

    # Remote tools, the External way (a broker) and the Custom way (a function): an act on a name
    # the agent does not own goes out to whichever the host composed, and comes back as Data.
    def test_should_call_out_through_remote_tools_the_host_supplies(self) -> None:
        # given
        input_prompt = create_random_string()
        remote_answer = create_random_string()
        remote_calls = []

        async def remote_tool(name: str, input: str) -> str:
            remote_calls.append((name, input))

            return remote_answer

        brain = RecordingBrainThatActsFirst("weather", "today")
        broker_brain = RecordingBrainThatActsFirst("weather", "today")
        broker = RecordingMcpBroker(remote_answer)
        custom_agent = StandardAgent().on_mcp(remote_tool).use_generator(brain)
        external_agent = StandardAgent().use_mcp(broker).use_generator(broker_brain)

        # when
        asyncio.run(custom_agent.run(input_prompt))
        asyncio.run(external_agent.run(input_prompt))

        # then
        assert remote_calls == [("weather", "today")]
        assert broker.calls == [("weather", "today")]
        assert f"weather returned: {remote_answer}" in brain.calls[1][1]
        assert f"weather returned: {remote_answer}" in broker_brain.calls[1][1]


class RecordingBrainThatActsFirst(IGeneratorBroker):
    def __init__(self, tool_name: str, tool_input: str) -> None:
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))

        if len(self.calls) == 1:
            return f"ACTION: {self.tool_name}: {self.tool_input}"

        return "FINAL: done"


class RecordingMcpBroker(IMcpBroker):
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[tuple[str, str]] = []

    async def call(self, name: str, input: str) -> str:
        self.calls.append((name, input))

        return self.answer

    async def list_tools(self) -> list[RemoteTool]:
        return []


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


class UndescribedTool(ITool):
    @property
    def name(self) -> str:
        return "hidden"

    async def execute(self, input: str) -> str:
        return "still runs"


class TestStandardAgentToolAdvertisement:
    # SPEC.md 6.1: a description is the opt-in. A tool without one is callable but never
    # advertised: absent from the catalog the brain reads, yet still run if the brain names it.
    def test_should_advertise_only_described_tools_and_still_run_the_rest(self) -> None:
        # given
        brain_calls = []

        async def skills() -> list[Skill]:
            return [Skill(name="skill.md", content="{{tools}}")]

        async def brain(system_prompt: str, user_prompt: str) -> str:
            brain_calls.append((system_prompt, user_prompt))

            if len(brain_calls) == 1:
                return "ACTION: hidden: x"

            return "FINAL: done"

        agent = (StandardAgent()
            .on_skills(skills)
            .tools([NamedTool("shown"), UndescribedTool()])
            .on_brain(brain))

        # when
        asyncio.run(agent.run(create_random_string()))

        # then
        assert brain_calls[0][0] == "- shown: the shown tool"
        assert "hidden returned: still runs" in brain_calls[1][1]
