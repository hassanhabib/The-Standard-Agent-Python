# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Enforced selection (SPEC.md 4.15): selection narrows what a run is SHOWN, and a brain the loop
# fully mediates can only call what it was shown. But a brain is configuration (a custom brain, a
# gateway, a model router) and configuration can carry side-channel knowledge of the catalog.
# With enforcement on, the offering also BINDS at the Direction perimeter: an act naming an
# advertised tool the run was not offered is denied (told, non-terminal, recoverable) exactly as
# a policy denial is. Off by default; the 4.15 treatment of an unoffered tool (reachable if the
# Brain names it) remains the unamended behavior.

from collections.abc import Awaitable, Callable, Sequence
from unittest.mock import create_autospec

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ModelToolCall,
    ToolDefinition)
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool

_Reply = Callable[[Sequence[ConversationMessage], Sequence[ToolDefinition]], GenerationResult]


class _NamedTool(Tool):
    def __init__(self, name: str, description: str | None = None) -> None:
        self._name = name
        self._description = f"The {name} tool." if description is None else description
        self.executions = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> str:
        return '{"type":"object"}'

    async def execute(self, input: str) -> str:
        self.executions += 1

        return "ran"


def _selecting(*names: str) -> Callable[[str, Sequence[str]], Awaitable[Sequence[str]]]:
    async def select_tools(task: str, described: Sequence[str]) -> Sequence[str]:
        return list(names)

    return select_tools


def _agent_with(reply: _Reply, *tools: Tool) -> StandardAgent:
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = [Skill(content="You are an assistant.")]

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    async def native_brain(messages, offered_tools) -> GenerationResult:
        return reply(messages, offered_tools)

    agent = (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .on_native_brain(native_brain))

    for tool in tools:
        agent = agent.tool(tool)

    return agent


def _calls_then_answers(
        tool_name: str,
        answer: str,
        on_second_turn: Callable[[Sequence[ConversationMessage]], None] | None = None) -> _Reply:
    """A brain that names a tool on its first decision and answers on its second: the shape of
    every disobedient-brain scenario below."""
    brain_calls = 0

    def reply(messages, tools) -> GenerationResult:
        nonlocal brain_calls
        brain_calls += 1

        if brain_calls == 1:
            return GenerationResult(
                content="",
                tool_calls=(ModelToolCall("call_1", tool_name, "{}"),))

        if on_second_turn is not None:
            on_second_turn(messages)

        return GenerationResult(content=answer)

    return reply


async def test_should_deny_an_unoffered_tool_when_the_offering_is_enforced():
    # given: the run is offered only the calculator, yet the brain names web_search anyway
    web_search = _NamedTool("web_search")
    calculator = _NamedTool("calculator")
    second_turn_messages: list[Sequence[ConversationMessage]] = []

    agent = (_agent_with(
            _calls_then_answers(
                "web_search",
                "answered among what was offered",
                second_turn_messages.append),
            web_search,
            calculator)
        .on_select_tools(_selecting("calculator"))
        .enforce_selection())

    # when
    result = await agent.process_prompt("what is 2 + 2?")

    # then: the act never ran, the denial was told, and the run recovered
    assert web_search.executions == 0
    assert result == "answered among what was offered"

    assert any(
        message.content is not None and "not offered" in message.content
        for message in second_turn_messages[-1])


# Off by default: without enforcement, an unoffered tool keeps its 4.15 treatment (reachable if
# the Brain names it), so no existing deployment changes behavior.
async def test_should_keep_an_unoffered_tool_reachable_without_enforcement():
    # given: the same disobedient brain, with no enforcement configured
    web_search = _NamedTool("web_search")
    calculator = _NamedTool("calculator")

    agent = (_agent_with(_calls_then_answers("web_search", "done"), web_search, calculator)
        .on_select_tools(_selecting("calculator")))

    # when
    result = await agent.process_prompt("what is 2 + 2?")

    # then: the unamended behavior: the named tool ran
    assert web_search.executions == 1
    assert result == "done"


# Enforcement takes effect only when a selector recorded an offering: with no selector there is
# nothing to enforce, and every described tool remains offered and callable.
async def test_should_not_deny_anything_when_no_selector_is_configured():
    # given: enforcement on, but no selection judgment supplied
    web_search = _NamedTool("web_search")

    agent = (_agent_with(_calls_then_answers("web_search", "done"), web_search)
        .enforce_selection())

    # when
    result = await agent.process_prompt("look something up")

    # then
    assert web_search.executions == 1
    assert result == "done"


# A name selection never saw is not selection's to withhold: an undescribed tool keeps its 6.1
# treatment (callable if the Brain names it, never advertised) under enforcement too.
async def test_should_not_deny_an_undescribed_tool():
    # given: a tool with no description (selection operates over described names only) and a
    # selector that offers nothing
    undescribed = _NamedTool("secret_helper", description="")

    agent = (_agent_with(_calls_then_answers("secret_helper", "done"), undescribed)
        .on_select_tools(_selecting())
        .enforce_selection())

    # when
    result = await agent.process_prompt("hello")

    # then
    assert undescribed.executions == 1
    assert result == "done"


# Caller tools are the caller's own vocabulary and are never subject to selection (SPEC.md
# 4.15): under enforcement, a call naming one still goes back to the caller as a pending effect,
# classified before the perimeter, so there is nothing here to deny.
async def test_should_never_deny_a_caller_tool():
    # given: enforcement on and an offering of nothing; the brain names the CALLER's tool
    agent = (_agent_with(
            lambda messages, tools: GenerationResult(
                content="",
                tool_calls=(ModelToolCall("call_9", "send_email", '{"to":"jane"}'),)))
        .on_select_tools(_selecting())
        .enforce_selection())

    request = PromptRequest(
        prompt="email jane the report",
        caller_tools=(
            ToolDefinition(
                name="send_email",
                description="Sends an email from the caller's own outbox.",
                parameters_json="{}"),))

    # when
    outcome = await agent.run(request)

    # then: the run paused for the caller rather than denying or refusing
    assert outcome.status is AgentStatus.AWAITING_INPUT
    assert outcome.pending_effect is not None
    assert outcome.pending_effect.tool_name == "send_email"
