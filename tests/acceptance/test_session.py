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
from collections.abc import Callable, Sequence
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.sessions.file_session_broker import FileSessionBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    MessageRole,
    ModelToolCall)
from standard_agents.models.coordinations.agents.exceptions import (
    AgentCoordinationValidationException)
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


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


# Found in the 2026-09-04 principal review (F-06): a session id is caller-provided and the record
# carried no owner, so two callers sharing or guessing one id shared one history. A session
# records the principal that opened it, and a different principal is refused as a validation
# failure, never served a quietly shared conversation.
async def test_should_refuse_a_session_owned_by_another_principal(tmp_path):
    # given
    sessions_path = str(tmp_path / "sessions")

    adas_agent = (_new_agent(sessions_path, lambda user_prompt: "FINAL: noted")
        .principal(lambda: "ada"))

    bobs_agent = (_new_agent(sessions_path, lambda user_prompt: "FINAL: noted")
        .principal(lambda: "bob"))

    await adas_agent.process_prompt("remember my order", session_id="order-42")

    # when
    bobs_prompt = bobs_agent.process_prompt("what was the order?", session_id="order-42")

    # then
    with pytest.raises(AgentCoordinationValidationException):
        await bobs_prompt


# Found in the 2026-09-04 principal review (F-06): a save was read, append, whole-record upsert,
# so two prompts in one session could both read the old history and the last writer erased the
# other's completed turn. Every write carries the version it was based on, the store refuses a
# stale one, and the loop re-reads and tries again.
async def test_should_keep_every_turn_when_prompts_run_concurrently_in_one_session(tmp_path):
    # given
    sessions_path = str(tmp_path / "sessions")
    agent = _new_agent(sessions_path, lambda user_prompt: "FINAL: noted")
    prompts = [f"fact number {index}" for index in range(8)]

    # when
    await asyncio.gather(*(
        agent.process_prompt(prompt, session_id="busy-session")
        for prompt in prompts))

    # then: every prompt's turn is in the history, whichever order they landed in
    session = await FileSessionBroker(sessions_path).select_session("busy-session")

    assert session is not None
    assert sorted(turn.prompt for turn in session.history) == sorted(prompts)


class _CalculatorTool(Tool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates arithmetic."

    @property
    def parameters(self) -> str:
        return '{"type":"object","properties":{"expression":{"type":"string"}}}'

    async def execute(self, input: str) -> str:
        return "4183"


def _new_native_agent(
        sessions_path: str,
        tool: Tool,
        reply: Callable[[Sequence[ConversationMessage]], GenerationResult]) -> StandardAgent:

    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = []

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    async def generate(messages, tools):
        return reply(messages)

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .tool(tool)
        .on_native_brain(generate)
        .sessions(sessions_path))


def _calculating_once_then_answering(conversations: list):
    """A native brain that asks for the calculator on its first call and answers after that,
    keeping the conversation it was handed on its third call: the follow-up prompt's."""
    brain_calls = 0

    def reply(messages):
        nonlocal brain_calls
        call = brain_calls
        brain_calls += 1

        if call == 0:
            return GenerationResult(tool_calls=(
                ModelToolCall("call_7", "calculator", '{"expression":"47*89"}'),))

        if call == 2:
            conversations.append(messages)

        return GenerationResult(content="4183")

    return reply


# A session that forgets its tool work is wrong in the same way a session that forgets an answer
# would be. AgentTurn carries a prompt and an answer and nothing else, so the call the agent made
# on the first prompt and the result it acted on are dropped at the save and can never be
# recalled: the next prompt is told what the agent said, never what it did in order to be able to
# say it. The conversation the Brain sees on the follow-up must still carry the assistant's
# request and the tool's answer against the id that asked for it, which is the one thing narrated
# prose cannot express (SPEC.md 4.11, SPEC.md 6).
async def test_should_carry_a_tool_exchange_across_prompts_in_one_session(tmp_path):
    # given
    follow_up_conversations = []

    agent = _new_native_agent(
        str(tmp_path / "sessions"),
        _CalculatorTool(),
        _calculating_once_then_answering(follow_up_conversations))

    # when
    await agent.process_prompt("what is 47 times 89?", session_id="user-13")
    await agent.process_prompt("how did you get that?", session_id="user-13")

    # then: the follow-up still carries the call and the answer that names it
    follow_up_conversation = follow_up_conversations[-1] if follow_up_conversations else []

    request = next(
        (message for message in follow_up_conversation
            if message.role is MessageRole.ASSISTANT and message.tool_calls),
        None)

    answer = next(
        (message for message in follow_up_conversation if message.role is MessageRole.TOOL),
        None)

    assert request is not None
    assert request.tool_calls[0].id == "call_7"

    assert answer is not None
    assert answer.tool_call_id == "call_7"
    assert answer.content == "4183"


# The other half of the same property. Once a turn carries its calls, those calls have to be as
# session-scoped as its words already are: one agent instance serving two conversations must
# never hand one conversation's call to the other. Keeping the exchanges anywhere but the session,
# on the instance or in a module global, satisfies the carrying test above and leaks here, and
# nothing else in this suite would notice: every other session test runs with no tools.
async def test_should_not_carry_one_sessions_tool_exchange_into_another(tmp_path):
    # given
    other_conversations = []

    agent = _new_native_agent(
        str(tmp_path / "sessions"),
        _CalculatorTool(),
        _calculating_once_then_answering(other_conversations))

    # when: one instance, two conversations
    await agent.process_prompt("what is 47 times 89?", session_id="alice")
    await agent.process_prompt("what is the capital of France?", session_id="bob")

    # then: bob is handed neither alice's call nor the answer that names it
    other_conversation = other_conversations[-1] if other_conversations else []

    assert not any(message.role == MessageRole.TOOL for message in other_conversation)

    assert not any(
        message.role == MessageRole.ASSISTANT and message.tool_calls
        for message in other_conversation)
