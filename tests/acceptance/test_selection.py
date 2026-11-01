# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Selection (SPEC.md 4.15): what an agent CARRIES and what a run is OFFERED are different things.
# A selector names the subset of described tools the run is offered; the Brain decides among what
# was offered; the perimeter never moves. A greeting is offered nothing, and a model cannot
# over-call a tool it was never shown.

from collections.abc import Awaitable, Callable, Sequence
from unittest.mock import create_autospec

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.brokers.audits.audit_record import AuditRecord
from standard_agents.models.brokers.generators.v1.conversation import (
    GenerationResult,
    ModelToolCall,
    ToolDefinition)
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


class _NamedTool(Tool):
    def __init__(self, name: str) -> None:
        self._name = name
        self.executions = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"The {self._name} tool."

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


def _brokers_with(skill: Skill) -> tuple[SkillBroker, MemoryBroker, KnowledgeBroker]:
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = [skill]

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    return skill_broker, memory_broker, knowledge_broker


def _agent_with(
        reply: Callable[[Sequence[ToolDefinition]], GenerationResult],
        *tools: Tool) -> StandardAgent:

    skill_broker, memory_broker, knowledge_broker = _brokers_with(
        Skill(content="You are an assistant."))

    async def native_brain(messages, offered_tools) -> GenerationResult:
        return reply(offered_tools)

    agent = (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .on_native_brain(native_brain))

    for tool in tools:
        agent = agent.tool(tool)

    return agent


def _text_agent_with(
        brain: Callable[[str, str], Awaitable[str]],
        *tools: Tool) -> StandardAgent:

    skill_broker, memory_broker, knowledge_broker = _brokers_with(
        Skill(content="You are an assistant.\n\nTools:\n{{tools}}"))

    agent = (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .on_brain(brain))

    for tool in tools:
        agent = agent.tool(tool)

    return agent


async def test_should_expand_the_tools_marker_with_only_the_selected_tools():
    # given: a text-protocol agent advertising through the {{tools}} marker
    seen_system_prompts = []

    async def brain(system_prompt: str, user_prompt: str) -> str:
        seen_system_prompts.append(system_prompt)

        return "FINAL: ok"

    agent = (_text_agent_with(brain, _NamedTool("web_search"), _NamedTool("code_search"))
        .on_select_tools(_selecting("web_search")))

    # when
    await agent.process_prompt("look something up")

    # then: the catalog the Brain reads lists the offered tool and nothing else
    seen_system_prompt = seen_system_prompts[-1]

    assert "web_search" in seen_system_prompt
    assert "code_search" not in seen_system_prompt


# A selector is configuration, and configuration can drift: a name the agent does not carry is
# ignored (SPEC.md 4.15), and the decision log records the TRUTH of what was offered, never the
# selector's claim.
async def test_should_ignore_selector_names_the_agent_does_not_carry():
    # given
    trace: list[AuditRecord] = []

    async def write(record: AuditRecord) -> None:
        trace.append(record)

    agent = (_agent_with(
            lambda tools: GenerationResult(content="hello!"),
            _NamedTool("web_search"),
            _NamedTool("code_search"))
        .on_select_tools(_selecting("a_tool_from_last_year", "web_search"))
        .on_audit(write))

    # when
    await agent.process_prompt("look something up")

    # then: the built-in remember tool is described too, and the trace says so: the record
    # states the truth of the whole offering, the framework's own tools included
    assert any(
        record.message == "Selection → offered [web_search]; withheld [code_search, remember]"
        for record in trace)


# An empty selection is a valid selection: the run is offered nothing, the greeting case.
async def test_should_offer_nothing_on_an_empty_selection():
    # given
    shown: list[Sequence[ToolDefinition]] = [[]]

    def reply(tools: Sequence[ToolDefinition]) -> GenerationResult:
        shown[0] = tools

        return GenerationResult(content="hello!")

    agent = (_agent_with(reply, _NamedTool("web_search"), _NamedTool("code_search"))
        .on_select_tools(_selecting()))

    # when
    answer = await agent.process_prompt("hi there")

    # then
    assert answer == "hello!"
    assert len(shown[0]) == 0


# Caller tools are the caller's own vocabulary (SPEC.md 4.13); selection governs the agent's tools
# and never the caller's: an empty selection still advertises them.
async def test_should_never_select_away_the_callers_tools():
    # given
    shown: list[Sequence[ToolDefinition]] = [[]]

    def reply(tools: Sequence[ToolDefinition]) -> GenerationResult:
        shown[0] = tools

        return GenerationResult(content="done")

    agent = (_agent_with(reply, _NamedTool("web_search"))
        .on_select_tools(_selecting()))

    request = PromptRequest(
        prompt="read a file",
        caller_tools=(ToolDefinition("read_file", "Reads a file.", "{}"),))

    # when
    await agent.process_prompt(request)

    # then
    assert any(definition.name == "read_file" for definition in shown[0])
    assert not any(definition.name == "web_search" for definition in shown[0])


# Selection narrows the OFFERING only (SPEC.md 4.15): an unselected tool behaves exactly like an
# undescribed one, reachable if the Brain names it, governed by the same perimeter, never offered.
# The callable surface never shrinks per run.
async def test_should_keep_an_unselected_tool_callable_by_name():
    # given: the selection offers web_search only, but the Brain names code_search anyway
    code_search = _NamedTool("code_search")
    calls = 0

    def reply(tools: Sequence[ToolDefinition]) -> GenerationResult:
        nonlocal calls
        calls += 1

        if calls == 1:
            return GenerationResult(tool_calls=(ModelToolCall("call_1", "code_search", "{}"),))

        return GenerationResult(content="done")

    agent = (_agent_with(reply, _NamedTool("web_search"), code_search)
        .on_select_tools(_selecting("web_search")))

    # when
    answer = await agent.process_prompt("search the code")

    # then
    assert answer == "done"
    assert code_search.executions == 1
