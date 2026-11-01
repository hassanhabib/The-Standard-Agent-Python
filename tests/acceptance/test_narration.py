# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Narration (SPEC.md 6.0): the agent says what it is doing, in the user's language, on a typed
# channel of its own. The prose is model-authored (a SAY: line) or tool-declared (a template
# floor), and either way it is user-visible output, so it crosses to the stream only after the
# Gate has screened it (Invariant 5: output MUST NOT cross a boundary un-vetted).

from collections.abc import Awaitable, Callable
from unittest.mock import create_autospec

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.sessions.session_broker import SessionBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.brokers.audits.audit_record import AuditRecord
from standard_agents.models.brokers.sessions.agent_session import AgentSession
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


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


def _scripted_brain(first_reply: str, then_reply: str) -> Callable[[str, str], Awaitable[str]]:
    calls = 0

    async def brain(system_prompt: str, user_prompt: str) -> str:
        nonlocal calls
        calls += 1

        return first_reply if calls == 1 else then_reply

    return brain


class _ScriptedTool(Tool):
    def __init__(self, name: str, output: str) -> None:
        self._name = name
        self._output = output
        self.executions = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "A scripted tool."

    async def execute(self, input: str) -> str:
        self.executions += 1

        return self._output


class _NarratingTool(Tool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "A scripted tool."

    @property
    def narration_starting(self) -> str:
        return "Searching with {tool} for {payload}..."

    @property
    def narration_observed(self) -> str:
        return "Got results from {tool}."

    async def execute(self, input: str) -> str:
        return "4"


async def _drain(agent: StandardAgent, prompt: str | PromptRequest) -> list[AgentStreamEvent]:
    return [stream_event async for stream_event in agent.process_prompt_stream(prompt)]


def _index_of(events: list[AgentStreamEvent], matches: Callable[[AgentStreamEvent], bool]) -> int:
    return next((index for index, event in enumerate(events) if matches(event)), -1)


def _answer_of(events: list[AgentStreamEvent]) -> str:
    return "".join(
        stream_event.content for stream_event in events
        if stream_event.type is AgentStreamEventType.RESPONSE)


async def test_should_screen_and_emit_model_narration_on_stream():
    # given
    tool = _ScriptedTool("calculator", "4")
    screened: list[str] = []

    async def gate(gate_rubric: str, text: str) -> str:
        screened.append(text)

        return "allow"

    agent = (_bare_agent(_scripted_brain(
            "SAY: Checking the calculator...\nACTION: calculator: 2+2",
            "FINAL: 4"))
        .tool(tool)
        .on_gate(gate))

    # when
    events = await _drain(agent, "what is 2+2?")

    # then: the narration is voiced before the act it announces, and the gate saw it first
    assert any(
        stream_event.type is AgentStreamEventType.NARRATION
        and stream_event.content == "Checking the calculator..."
        for stream_event in events)

    narration_index = _index_of(
        events, lambda stream_event: stream_event.type is AgentStreamEventType.NARRATION)

    tool_index = _index_of(
        events, lambda stream_event: stream_event.type is AgentStreamEventType.TOOL)

    assert tool_index > narration_index
    assert _answer_of(events) == "4"
    assert "Checking the calculator..." in screened


# A refused narration is withheld silently and recorded loudly: the user gains nothing from "a
# progress note was withheld", and echoing the refusal would hand an injected SAY payload a
# visible oracle, but the decision log carries the fact, which is where a review looks (SPEC.md
# 4.7). The run itself is unharmed: narration is decoration, never the work.
async def test_should_withhold_refused_narration_and_record_it_on_stream():
    # given
    tool = _ScriptedTool("calculator", "4")
    trace: list[AuditRecord] = []

    async def gate(gate_rubric: str, text: str) -> str:
        return "refuse: prompt injection" if "Checking the calculator" in text else "allow"

    async def write(record: AuditRecord) -> None:
        trace.append(record)

    agent = (_bare_agent(_scripted_brain(
            "SAY: Checking the calculator...\nACTION: calculator: 2+2",
            "FINAL: 4"))
        .tool(tool)
        .on_gate(gate)
        .on_audit(write))

    # when
    events = await _drain(agent, "what is 2+2?")

    # then: nothing voiced, the run unharmed, the record carrying the fact
    assert not any("Checking the calculator" in stream_event.content for stream_event in events)
    assert _answer_of(events) == "4"

    assert any(
        "Narration" in record.message and "WITHHELD" in record.message
        for record in trace)


# The floor: a tool that declared its narration is voiced even when the model said nothing; the
# run never goes silent just because the model was terse.
async def test_should_voice_tool_narration_floor_when_model_says_nothing_on_stream():
    # given
    agent = (_bare_agent(_scripted_brain("ACTION: calculator: 2+2", "FINAL: 4"))
        .tool(_NarratingTool()))

    # when
    events = await _drain(agent, "what is 2+2?")

    # then: both slots voiced, interpolated, and in the story's order: the announcement, the
    # observation, then the Tool event carrying the data
    starting_index = _index_of(
        events,
        lambda stream_event: stream_event.type is AgentStreamEventType.NARRATION
            and stream_event.content == "Searching with calculator for 2+2...")

    observed_index = _index_of(
        events,
        lambda stream_event: stream_event.type is AgentStreamEventType.NARRATION
            and stream_event.content == "Got results from calculator.")

    tool_index = _index_of(
        events, lambda stream_event: stream_event.type is AgentStreamEventType.TOOL)

    assert starting_index > -1
    assert observed_index > starting_index
    assert tool_index > observed_index


# Model narration beats the template for the pre-act slot: the model's grounded prose is the
# ceiling, the tool's template only the floor. The observed slot is never overridden: a SAY line
# speaks for the act, not for its outcome.
async def test_should_prefer_model_narration_over_tool_template_on_stream():
    # given
    agent = (_bare_agent(_scripted_brain(
            "SAY: Let me check the calculator...\nACTION: calculator: 2+2",
            "FINAL: 4"))
        .tool(_NarratingTool()))

    # when
    events = await _drain(agent, "what is 2+2?")

    # then
    assert any(
        stream_event.type is AgentStreamEventType.NARRATION
        and stream_event.content == "Let me check the calculator..."
        for stream_event in events)

    assert not any("Searching with" in stream_event.content for stream_event in events)

    assert any(
        stream_event.type is AgentStreamEventType.NARRATION
        and stream_event.content == "Got results from calculator."
        for stream_event in events)


# Narration dies with its turn: it never enters the answer, the observations, or the session's
# history; the next turn's brain input and the saved conversation carry none of it (SPEC.md
# 4.11).
async def test_should_keep_narration_out_of_the_session_and_the_next_brain_input():
    # given
    tool = _ScriptedTool("calculator", "4")
    calls = 0
    brain_inputs: list[str] = []
    saved_sessions: list[AgentSession] = []

    session_broker = create_autospec(SessionBroker, instance=True)
    session_broker.select_session.return_value = None
    session_broker.upsert_session.side_effect = saved_sessions.append

    async def brain(system_prompt: str, user_message: str) -> str:
        nonlocal calls
        brain_inputs.append(user_message)
        calls += 1

        return (
            "SAY: Checking the calculator...\nACTION: calculator: 2+2" if calls == 1
            else "FINAL: 4")

    agent = (_bare_agent(brain)
        .tool(tool)
        .use_sessions(session_broker))

    request = PromptRequest(prompt="what is 2+2?", session_id="session-1")

    # when
    await _drain(agent, request)

    # then
    assert all("Checking the calculator" not in brain_input for brain_input in brain_inputs)

    assert all(
        "Checking the calculator" not in turn.prompt
        and "Checking the calculator" not in turn.answer
        for session in saved_sessions
        for turn in session.history)
