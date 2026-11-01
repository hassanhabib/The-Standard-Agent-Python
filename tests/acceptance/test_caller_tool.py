# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Caller tools (docs/per-request-inference.md 6).

In the OpenAI protocol the server never executes a caller's tool: the model names one, the
server returns the call, and the CALLER executes it and posts the result back. Caller tools are
therefore vocabulary handed to the model, never capability granted to the agent, and a call
naming one is a terminal answer addressed to the caller, riding the same pending-effect seam a
held approval rides.
"""

from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.sessions.file_session_broker import FileSessionBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    MessageRole,
    ModelToolCall,
    ToolDefinition)
from standard_agents.models.brokers.sessions.agent_session import AgentTurn
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


@pytest.fixture
def sessions_path(tmp_path):
    return str(tmp_path / "standard-agent-caller-tools")


def _bare_agent() -> StandardAgent:
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = [Skill(content="You are a helpful agent.")]

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker))


def _agent_with(brain) -> StandardAgent:
    return _bare_agent().on_brain(brain)


def _send_email_tool() -> ToolDefinition:
    return ToolDefinition(
        name="send_email",
        description="Sends an email from the caller's own outbox.",
        parameters_json="{}")


# The foreign call is a pending effect: the run pauses, something outside this process must act
# and report back. Built for human approval, structurally identical here. The authority over
# this one is the caller.
async def test_should_treat_a_call_naming_a_caller_tool_as_a_terminal_answer(sessions_path):
    # given: a brain that wants the caller's tool, which the agent cannot and must not run
    async def brain(system_prompt, user_prompt):
        return 'ACTION: send_email: {"to":"jane@acme.com"}'

    agent = (_agent_with(brain)
        .sessions(sessions_path)
        .max_turns(2))

    request = PromptRequest(
        prompt="email jane the report",
        session_id="caller-run-1",
        caller_tools=(_send_email_tool(),))

    # when
    outcome = await agent.run(request)

    # then: the run paused rather than recovered, refused, or executed anything
    assert outcome.status is AgentStatus.AWAITING_INPUT
    assert "send_email" in outcome.result

    # and the call itself rode out on the session, so a different process can hand the caller
    # the act rather than only the news that something is waiting
    session = await FileSessionBroker(sessions_path).select_session("caller-run-1")

    assert session is not None
    assert session.pending_effect is not None
    assert session.pending_effect.tool_name == "send_email"
    assert "jane@acme.com" in session.pending_effect.arguments


class _RecordingNativeBroker(GeneratorBrokerV1):
    def __init__(self) -> None:
        self.captured_tools: tuple[ToolDefinition, ...] = ()

    async def generate(self, messages, tools, *, inference=None):
        self.captured_tools = tuple(tools)

        return GenerationResult(content="ok")


class _CalculatorTool(Tool):
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
        return "4183"


# One vocabulary, two owners: the model sees the configured tools and the caller's tools side
# by side, and only Direction knows which words are whose (design 6.1).
async def test_should_advertise_caller_tools_beside_configured_ones_natively():
    # given
    broker = _RecordingNativeBroker()

    agent = (_bare_agent()
        .tool(_CalculatorTool())
        .use_native_brain(broker))

    request = PromptRequest(prompt="hello", caller_tools=(_send_email_tool(),))

    # when
    await agent.process_prompt(request)

    # then
    assert any(tool.name == "calculator" for tool in broker.captured_tools)
    assert any(tool.name == "send_email" for tool in broker.captured_tools)


class _CountingCalculatorTool(Tool):
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


# Name collision resolved by the perimeter rule (design 6.1): configured wins, and unambiguously.
# A caller declaring a tool named like the deployment's own cannot shadow it. The call means the
# configured tool, executed locally, under every configured control.
async def test_should_let_the_configured_tool_keep_its_name():
    # given: the caller claims "calculator" for itself
    tool = _CountingCalculatorTool()
    call = 0

    async def brain(system_prompt, user_prompt):
        nonlocal call
        call += 1

        return "ACTION: calculator: 47*89" if call == 1 else "FINAL: 4183"

    agent = _agent_with(brain).tool(tool)

    request = PromptRequest(
        prompt="what is 47 times 89?",
        caller_tools=(
            ToolDefinition(
                name="calculator",
                description="The caller's own calculator.",
                parameters_json="{}"),))

    # when
    outcome = await agent.run(request)

    # then: executed here, not returned to the caller
    assert tool.execution_count == 1
    assert outcome.status is AgentStatus.RESPONDED
    assert outcome.result == "4183"


class _YieldingNativeBroker(GeneratorBrokerV1):
    async def generate(self, messages, tools, *, inference=None):
        return GenerationResult(
            tool_calls=(
                ModelToolCall(
                    id="call_9",
                    name="send_email",
                    arguments_json='{"to":"jane@acme.com"}'),))


# A stateless deployment has no session, and the client owns the transcript: the exposed
# protocol this seam exists for (docs/per-request-inference.md 6.2). The pending call must
# therefore reach the caller on the OUTCOME itself, carrying the id the model minted, or the
# exposer cannot render the yield at all.
async def test_should_hand_the_caller_their_call_on_the_outcome_without_a_session():
    # given: no sessions configured, a native brain that wants the caller's tool
    agent = _bare_agent().use_native_brain(_YieldingNativeBroker())

    request = PromptRequest(
        prompt="email jane the report",
        caller_tools=(_send_email_tool(),))

    # when
    outcome = await agent.run(request)

    # then: the call itself, on the outcome, with the model's own id
    assert outcome.status is AgentStatus.AWAITING_INPUT
    assert outcome.pending_effect is not None
    assert outcome.pending_effect.tool_name == "send_email"
    assert outcome.pending_effect.call_id == "call_9"
    assert "jane@acme.com" in outcome.pending_effect.arguments


class _MessageRecordingNativeBroker(GeneratorBrokerV1):
    def __init__(self) -> None:
        self.captured_messages: tuple[ConversationMessage, ...] = ()

    async def generate(self, messages, tools, *, inference=None):
        self.captured_messages = tuple(messages)

        return GenerationResult(content="ok")


# The exposed protocols this seam exists for are stateless: the client re-posts the whole
# conversation, prior tool exchanges included. A run that cannot receive that transcript starts
# from nothing every time, and the second half of the yield (the caller answering a call the
# run handed out) becomes impossible to express.
async def test_should_carry_the_caller_owned_transcript_to_the_native_brain():
    # given
    broker = _MessageRecordingNativeBroker()
    agent = _bare_agent().use_native_brain(broker)

    request = PromptRequest(
        prompt="and then?",
        history=(AgentTurn("What is 2+2?", "4"),),
        tool_exchanges=(
            ToolExchange(
                call_id="call_9",
                tool_name="send_email",
                arguments_json='{"to":"jane@acme.com"}',
                result="sent"),))

    # when
    await agent.process_prompt(request)

    # then: the prior turn as user and assistant messages, and the exchange as a tool message
    # still naming the call the model minted
    assert any(
        message.role is MessageRole.USER and message.content == "What is 2+2?"
        for message in broker.captured_messages)

    assert any(
        message.role is MessageRole.ASSISTANT and message.content == "4"
        for message in broker.captured_messages)

    assert any(
        message.role is MessageRole.TOOL
        and message.tool_call_id == "call_9"
        and message.content == "sent"
        for message in broker.captured_messages)


# The same transcript on the text protocol: history renders into the conversation the model is
# shown, exactly as a session's history would.
async def test_should_carry_the_caller_owned_transcript_on_the_text_protocol():
    # given
    captured_user_prompt = ""

    async def brain(system_prompt, user_prompt):
        nonlocal captured_user_prompt
        captured_user_prompt = user_prompt

        return "FINAL: ok"

    agent = _bare_agent().on_brain(brain)

    request = PromptRequest(
        prompt="and then?",
        history=(AgentTurn("What is 2+2?", "4"),))

    # when
    await agent.process_prompt(request)

    # then
    assert "What is 2+2?" in captured_user_prompt
    assert "4" in captured_user_prompt
