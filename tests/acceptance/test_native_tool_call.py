# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Native tool calling (SPEC.md 6). The text protocol asks a model to imitate a format; a tool_call
# is the thing hosted models are actually tuned for. These pin that adopting it changes how a
# choice is READ, not what the agent is: the same tools, the same perimeter, the same answer at
# the end.

from collections.abc import Callable, Sequence
from unittest.mock import call, create_autospec

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    MessageRole,
    ModelToolCall,
    ToolDefinition)
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


class _CalculatorTool(Tool):
    def __init__(self) -> None:
        self.received_inputs: list[str] = []

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
        self.received_inputs.append(input)

        return "4183"


class _UndescribedTool(Tool):
    @property
    def name(self) -> str:
        return "secret"

    @property
    def description(self) -> str:
        return ""

    @property
    def parameters(self) -> str:
        return "{}"

    async def execute(self, input: str) -> str:
        return "never advertised"


def _agent_with(
        tool: _CalculatorTool,
        reply: Callable[[Sequence[ToolDefinition], int], GenerationResult]) -> StandardAgent:

    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = [Skill(content="You are a calculator agent.")]

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    calls = 0

    async def native_brain(messages, tools) -> GenerationResult:
        nonlocal calls
        result = reply(tools, calls)
        calls += 1

        return result

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .tool(tool)
        .on_native_brain(native_brain))


def _asks_then_answers(tools: Sequence[ToolDefinition], turn: int) -> GenerationResult:
    if turn == 0:
        return GenerationResult(tool_calls=(
            ModelToolCall(
                id="call_1",
                name="calculator",
                arguments_json='{"expression":"47*89"}'),))

    return GenerationResult(content="4183")


async def test_should_round_trip_a_native_tool_call():
    # given: the model asks for the tool, then answers from its result
    tool = _CalculatorTool()
    agent = _agent_with(tool, _asks_then_answers)

    # when
    actual_result = await agent.process_prompt("what is 47 times 89?")

    # then
    assert len(tool.received_inputs) == 1
    assert "47*89" in tool.received_inputs[0]
    assert actual_result == "4183"


# Found in the 2026-08-23 sweep: the streamed decision had no speaks-natively branch, so a
# native-brain agent asked to stream called the V0 text seam, which, for a native-only
# composition, is the placeholder that throws "This agent has a native brain; the text protocol
# is not in use." Adopting native calls changes how a choice is READ, not what the agent is, on
# every path a prompt can be processed (SPEC.md 6, 7.6).
async def test_should_round_trip_a_native_tool_call_when_streamed():
    # given: the identical scenario as the batched round-trip above
    tool = _CalculatorTool()
    agent = _agent_with(tool, _asks_then_answers)

    # when
    responses = [
        stream_event.content
        async for stream_event in agent.process_prompt_stream("what is 47 times 89?")
        if stream_event.type is AgentStreamEventType.RESPONSE]

    # then: the same tools, the same perimeter, the same answer at the end
    assert len(tool.received_inputs) == 1
    assert "".join(responses) == "4183"
