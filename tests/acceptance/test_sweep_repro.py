# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Review-sweep demonstrations (2026-08-23, docs/reviews/2026-08-23-full-sweep.md in the C#
# repository). Each test asserts the behaviour the spec or docs promise for one finding; the C#
# file kept them skipped while the finding was open and runs them now that it is resolved.

from collections.abc import Awaitable, Callable
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


class _CountingTool(Tool):
    def __init__(self, result: str = "4183") -> None:
        self._result = result
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

        return self._result


@pytest.fixture
def sessions_path(tmp_path) -> str:
    return str(tmp_path / "standard-agent-sweep")


def _bare_agent(brain: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
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
        .on_brain(brain))


async def _looping_brain(system_prompt: str, user_prompt: str) -> str:
    return "ACTION: calculator: 47*89"


# FINDING 7: a turn-capped run recorded the last tool output in the conversation as though it
# were the agent's answer. Skipped through 1.6.1 as the open demonstration; resolved by decision:
# a capped run stops without delivering an answer, like a budget stop.
async def test_finding7_turn_capped_run_must_not_record_an_answer_it_never_gave(sessions_path):
    tool = _CountingTool()

    capped = (_bare_agent(_looping_brain)
        .tool(tool)
        .sessions(sessions_path)
        .max_turns(2))

    await capped.process_prompt("loop", session_id="conv-1")

    follow_up_prompts: list[str] = []

    async def follower_brain(system_prompt: str, user_prompt: str) -> str:
        follow_up_prompts.append(user_prompt)

        return "FINAL: hello"

    follower = _bare_agent(follower_brain).sessions(sessions_path)

    await follower.process_prompt("hi again", session_id="conv-1")

    # the capped run never delivered an answer, and the next prompt must not be told the agent
    # said something it never said
    assert "4183" not in follow_up_prompts[-1]


# FINDING 7b: the outcome shape at the cap, as decided: the caller gets prose about why (what
# AgentOutcome's contract always promised), never the last tool output dressed as an answer, and
# the status stays WORKING because the run stopped mid-work rather than failing.
async def test_finding7_b_turn_cap_delivers_prose_about_why_with_status_working():
    tool = _CountingTool()

    capped = (_bare_agent(_looping_brain)
        .tool(tool)
        .max_turns(2))

    outcome = await capped.run("loop")

    # a run that never delivered an answer owes the caller prose about why, not the last
    # tool's raw output
    assert "out of turns" in outcome.result
    assert "4183" not in outcome.result
    assert outcome.status is AgentStatus.WORKING
