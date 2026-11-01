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


class EchoTool(ITool):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "repeats its input"

    async def execute(self, input: str) -> str:
        return input
