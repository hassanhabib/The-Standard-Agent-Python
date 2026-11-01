# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Conversation and resumption (SPEC.md 4.11).

Invariant 4 says the agent INSTANCE is stateless across prompts. It does not say the conversation
is. These pin that distinction: the same session continues across two separate agent instances,
which is the property that makes resumption real rather than incidental.
"""

import asyncio
from collections.abc import Callable
from unittest.mock import create_autospec

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.standard_agent import StandardAgent


def _new_agent(
        sessions_path: str,
        answer_for: Callable[[str], str],
        capture: Callable[[str], None] | None = None) -> StandardAgent:

    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = []

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    async def generate(system_prompt: str, user_prompt: str) -> str:
        if capture is not None:
            capture(user_prompt)

        return answer_for(user_prompt)

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .on_brain(generate)
        .sessions(sessions_path))


async def test_should_carry_conversation_across_prompts(tmp_path):
    # given
    captured_second_prompt = ""
    calls = 0

    def answer_for(user_prompt):
        nonlocal calls
        calls += 1

        return "FINAL: Paris" if calls == 1 else "FINAL: about 2.1 million"

    def capture(user_prompt):
        nonlocal captured_second_prompt

        if calls == 1:
            captured_second_prompt = user_prompt

    agent = _new_agent(str(tmp_path / "sessions"), answer_for, capture)

    # when
    await agent.process_prompt("what is the capital of France?", session_id="user-42")
    await agent.process_prompt("and its population?", session_id="user-42")

    # then: the follow-up carries what came before
    assert "capital of France" in captured_second_prompt
    assert "Paris" in captured_second_prompt


# The property that makes resumption real: the session is the state, the instance is not. An
# implementation whose continuity depends on the original instance still being alive has not
# implemented this (SPEC.md 4.11).
async def test_should_resume_a_conversation_on_a_different_agent_instance(tmp_path):
    # given: the first agent answers, then is discarded entirely
    sessions_path = str(tmp_path / "sessions")
    first_agent = _new_agent(sessions_path, lambda user_prompt: "FINAL: Paris")
    await first_agent.process_prompt("what is the capital of France?", session_id="user-7")
    del first_agent

    captured_prompts = []

    second_agent = _new_agent(
        sessions_path,
        answer_for=lambda user_prompt: "FINAL: about 2.1 million",
        capture=captured_prompts.append)

    # when: a different instance picks the conversation up
    await second_agent.process_prompt("and its population?", session_id="user-7")

    # then
    assert "Paris" in captured_prompts[-1]


async def test_should_keep_sessions_separate(tmp_path):
    # given
    captured_prompts = []

    agent = _new_agent(
        str(tmp_path / "sessions"),
        answer_for=lambda user_prompt: "FINAL: Paris",
        capture=captured_prompts.append)

    await agent.process_prompt("what is the capital of France?", session_id="alice")

    # when: a different conversation entirely
    await agent.process_prompt("what is the capital of Japan?", session_id="bob")

    # then: bob never sees alice's exchange
    assert "France" not in captured_prompts[-1]


async def test_should_not_record_a_cancelled_run_as_an_answer(tmp_path):
    # given
    sessions_path = str(tmp_path / "sessions")
    cancellation = asyncio.Event()
    cancellation.set()

    agent = _new_agent(sessions_path, lambda user_prompt: "FINAL: Paris")

    await agent.process_prompt(
        "what is the capital of France?",
        session_id="user-9",
        cancellation=cancellation)

    captured_prompts = []

    next_agent = _new_agent(
        sessions_path,
        answer_for=lambda user_prompt: "FINAL: anything",
        capture=captured_prompts.append)

    # when
    await next_agent.process_prompt("follow up", session_id="user-9")

    # then: the next prompt is never told the agent said something it never said
    assert "cancelled" not in captured_prompts[-1]
    assert "Paris" not in captured_prompts[-1]


async def test_should_stay_stateless_without_a_session(tmp_path):
    # given
    captured_prompt = ""
    calls = 0

    def answer_for(user_prompt):
        nonlocal calls
        calls += 1

        return "FINAL: Paris" if calls == 1 else "FINAL: anything"

    def capture(user_prompt):
        nonlocal captured_prompt

        if calls == 1:
            captured_prompt = user_prompt

    agent = _new_agent(str(tmp_path / "sessions"), answer_for, capture)

    # when: no session id at all
    await agent.process_prompt("what is the capital of France?")
    await agent.process_prompt("and its population?")

    # then: absent a session the agent is exactly as stateless as it always was
    assert "Paris" not in captured_prompt
