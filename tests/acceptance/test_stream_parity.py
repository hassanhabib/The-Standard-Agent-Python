# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# One prompt, two doors. Invariant 6 already says a control must hold "on every path by which a
# prompt can be processed", and names the batched and the streamed loop specifically. It says
# that about guardian neutralization, but the reason generalizes: a control a caller can step
# around by changing method is not a control.
#
# Budgets, cancellation and sessions were enforced on the batched path only.

import asyncio
from collections.abc import AsyncIterable, Awaitable, Callable
from datetime import timedelta
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


class _CountingTool(Tool):
    def __init__(self) -> None:
        self.execution_count = 0

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates arithmetic."

    @property
    def parameters(self) -> str:
        return "{}"

    async def execute(self, input: str) -> str:
        self.execution_count += 1

        return "4183"


@pytest.fixture
def sessions_path(tmp_path) -> str:
    return str(tmp_path / "standard-agent-stream")


def _agent_that_loops(
        tool: _CountingTool,
        brain: Callable[[str, str], Awaitable[str]]) -> StandardAgent:

    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = []

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .tool(tool)
        .on_brain(brain))


async def _drain(events: AsyncIterable[AgentStreamEvent]) -> list[AgentStreamEvent]:
    return [stream_event async for stream_event in events]


def _answering(reply: str) -> Callable[[str, str], Awaitable[str]]:
    async def brain(system_prompt: str, user_prompt: str) -> str:
        return reply

    return brain


async def test_should_stop_a_streamed_run_when_cancelled():
    # given: a model that would loop forever, and a token already cancelled
    tool = _CountingTool()
    cancellation = asyncio.Event()
    cancellation.set()

    agent = (_agent_that_loops(tool, _answering("ACTION: calculator: 47*89"))
        .max_turns(50))

    # when
    actual_events = await _drain(
        agent.process_prompt_stream("loop", cancellation=cancellation))

    # then: a cancelled run stops at the turn boundary and says so, on this path too
    assert tool.execution_count == 0
    assert any("cancelled" in stream_event.content for stream_event in actual_events)


async def test_should_stop_a_streamed_run_when_the_budget_is_exhausted():
    # given: a model that would loop forever, and no time to do it in
    tool = _CountingTool()

    agent = (_agent_that_loops(tool, _answering("ACTION: calculator: 47*89"))
        .max_turns(50)
        .budget(max_wall_clock=timedelta(0)))

    # when
    actual_events = await _drain(agent.process_prompt_stream("loop"))

    # then: a budget a caller can step around by streaming is not a budget
    assert any("budget" in stream_event.content for stream_event in actual_events)


async def test_should_carry_the_conversation_on_a_streamed_run(sessions_path):
    # given: the first prompt is answered on the batched path
    tool = _CountingTool()
    second_prompts: list[str] = []

    first = _agent_that_loops(tool, _answering("FINAL: Paris")).sessions(sessions_path)

    await first.process_prompt("what is the capital of France?", session_id="trip-3")

    # when: the follow-up is streamed
    async def second_brain(system_prompt: str, user_prompt: str) -> str:
        second_prompts.append(user_prompt)

        return "FINAL: about two million"

    second = _agent_that_loops(tool, second_brain).sessions(sessions_path)

    await _drain(second.process_prompt_stream(
        "and how many people live there?",
        session_id="trip-3"))

    # then: the streamed path loads the conversation like the batched one does
    assert "Paris" in second_prompts[-1]
