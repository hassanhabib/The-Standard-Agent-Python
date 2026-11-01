# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import uuid
from pathlib import Path

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.itool import ITool


# Acceptance: the whole agent, composed the way a user composes it, through the real brokers.
# Only the brain is a stand-in, because the brain is the one thing a test cannot own.
def create_random_string() -> str:
    return uuid.uuid4().hex


class TestStandardAgentRuns:
    def test_should_answer_through_the_brain(self) -> None:
        # given
        input_prompt = create_random_string()
        random_answer = create_random_string()
        expected_outcome = AgentOutcome(result=random_answer, status=AgentStatus.RESPONDED)

        async def brain(system_prompt: str, user_prompt: str) -> str:
            return f"FINAL: {random_answer}"

        agent = StandardAgent().on_brain(brain)

        # when
        actual_outcome = asyncio.run(agent.run(input_prompt))

        # then
        assert actual_outcome == expected_outcome

    # Skills from a folder (with the tool catalog written in at {{tools}}), a tool the agent owns,
    # and two turns: the first acts, the second answers from what it observed.
    def test_should_act_with_a_tool_and_then_answer(self, tmp_path: Path) -> None:
        # given
        input_prompt = create_random_string()
        random_instructions = create_random_string()
        tmp_path.joinpath("00-assistant.md").write_text(f"{random_instructions}\n{{{{tools}}}}")
        echo_tool = EchoTool()
        tool_input = create_random_string()
        brain_calls = []

        expected_system_prompt = (
            f"{random_instructions}\n- {echo_tool.name}: {echo_tool.description}")

        async def brain(system_prompt: str, user_prompt: str) -> str:
            brain_calls.append((system_prompt, user_prompt))

            if len(brain_calls) == 1:
                return f"ACTION: echo: {tool_input}"

            return f"FINAL: heard {tool_input}"

        expected_outcome = AgentOutcome(
            result=f"heard {tool_input}",
            status=AgentStatus.RESPONDED)

        agent = StandardAgent().skills(str(tmp_path)).tool(echo_tool).on_brain(brain)

        # when
        actual_outcome = asyncio.run(agent.run(input_prompt))

        # then
        assert actual_outcome == expected_outcome
        assert len(brain_calls) == 2
        assert brain_calls[0][0] == expected_system_prompt
        assert f"echo returned: {tool_input}" in brain_calls[1][1]

    # Data, end to end: memories from a file, knowledge from the caller's own function, both in
    # front of the brain before it decides.
    def test_should_recall_memories_and_knowledge_for_the_brain(self, tmp_path: Path) -> None:
        # given
        input_prompt = create_random_string()
        random_memory = create_random_string()
        random_knowledge = create_random_string()
        memory_file = tmp_path.joinpath("memory.txt")
        memory_file.write_text(f"{random_memory}\n\n")
        knowledge_queries = []
        brain_calls = []

        async def knowledge(query: str) -> list[str]:
            knowledge_queries.append(query)

            return [random_knowledge]

        async def brain(system_prompt: str, user_prompt: str) -> str:
            brain_calls.append(user_prompt)

            return "FINAL: done"

        expected_user_prompt = (
            f"Task: {input_prompt}\n\n"
            + "Observations so far:\n"
            + f"- {random_memory}\n"
            + f"- {random_knowledge}\n")

        agent = (StandardAgent()
            .memory(str(memory_file))
            .on_knowledge(knowledge)
            .on_brain(brain))

        # when
        asyncio.run(agent.run(input_prompt))

        # then
        assert knowledge_queries == [input_prompt]
        assert brain_calls == [expected_user_prompt]

    # Decision's guardians, end to end: the Gate refuses before the brain is ever asked, and the
    # Judge sends a weak draft back so only the reviewed answer is delivered.
    def test_should_refuse_when_the_gate_refuses(self) -> None:
        # given
        input_prompt = create_random_string()
        brain_calls = []

        async def gate(text: str) -> str:
            return "refuse: asks for secrets"

        async def brain(system_prompt: str, user_prompt: str) -> str:
            brain_calls.append(user_prompt)

            return "FINAL: secrets"

        expected_outcome = AgentOutcome(
            result="I'm not able to help with that.",
            status=AgentStatus.REFUSED)

        agent = StandardAgent().on_gate(gate).on_brain(brain)

        # when
        actual_outcome = asyncio.run(agent.run(input_prompt))

        # then
        assert actual_outcome == expected_outcome
        assert brain_calls == []

    def test_should_revise_when_the_judge_rejects_a_draft(self) -> None:
        # given
        input_prompt = create_random_string()
        weak_draft = create_random_string()
        strong_answer = create_random_string()
        drafts = [weak_draft, strong_answer]
        brain_calls = []

        async def brain(system_prompt: str, user_prompt: str) -> str:
            brain_calls.append(user_prompt)

            return f"FINAL: {drafts[len(brain_calls) - 1]}"

        async def judge(task: str, candidate: str) -> str:
            if candidate == weak_draft:
                return "0.1 too vague"

            return "0.9"

        expected_outcome = AgentOutcome(result=strong_answer, status=AgentStatus.RESPONDED)
        agent = StandardAgent().on_judge(judge).on_brain(brain)

        # when
        actual_outcome = asyncio.run(agent.run(input_prompt))

        # then
        assert actual_outcome == expected_outcome
        assert len(brain_calls) == 2
        assert "too vague" in brain_calls[1]

    # A brain that keeps acting and never answers is stopped at the bound, and the run says it
    # delivered nothing. Every turn is traced to the log the host chose.
    def test_should_stop_at_the_turn_limit_and_trace_every_turn(self, tmp_path: Path) -> None:
        # given
        input_prompt = create_random_string()
        log_file = tmp_path.joinpath("log.txt")
        brain_calls = []

        async def brain(system_prompt: str, user_prompt: str) -> str:
            brain_calls.append(user_prompt)

            return "ACTION: echo: again"

        expected_outcome = AgentOutcome(
            result="I ran out of turns before an answer was ready; nothing was delivered.",
            status=AgentStatus.FAILED)

        agent = (StandardAgent()
            .tool(EchoTool())
            .max_turns(2)
            .log_to(str(log_file))
            .on_brain(brain))

        # when
        actual_outcome = asyncio.run(agent.run(input_prompt))

        # then
        assert actual_outcome == expected_outcome
        assert len(brain_calls) == 2
        trace = log_file.read_text(encoding="utf-8")
        assert "Turn 0" in trace
        assert "Turn 1" in trace


class EchoTool(ITool):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "repeats its input"

    async def execute(self, input: str) -> str:
        return input
