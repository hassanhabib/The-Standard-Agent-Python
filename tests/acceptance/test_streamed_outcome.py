# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The streamed outcome (SPEC.md 4.14): one enumeration, every event live, and, once it completes,
# the SAME structured outcome the batched door returns. A caller never chooses between the
# answer's structure and the run's story.

from collections.abc import Awaitable, Callable
from unittest.mock import create_autospec

from standard_agents.agent import Agent
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
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


class _ScriptedTool(Tool):
    def __init__(self) -> None:
        self.executions = 0

    @property
    def name(self) -> str:
        return "wire_transfer"

    @property
    def description(self) -> str:
        return "A scripted tool."

    async def execute(self, input: str) -> str:
        self.executions += 1

        return "paid"


async def test_should_carry_the_held_act_on_the_streamed_outcome():
    # given: a run that ends held for approval: the batched door reports the hold and the act
    # itself; the streamed door must report exactly the same ending
    tool = _ScriptedTool()

    async def brain(system_prompt: str, user_prompt: str) -> str:
        return "ACTION: wire_transfer: 10"

    agent = (_bare_agent(brain)
        .tool(tool)
        .require_approval("wire_transfer"))

    # when: through the contract, which is where a host calls it
    contract: Agent = agent
    run_stream = contract.run_stream("pay the invoice")
    events = [stream_event async for stream_event in run_stream]

    # then: the events flowed AND the outcome is the batched door's, structure included
    assert len(events) > 0
    assert tool.executions == 0

    assert run_stream.outcome.status is AgentStatus.AWAITING_APPROVAL
    assert run_stream.outcome.pending_effect is not None
    assert run_stream.outcome.pending_effect.tool_name == "wire_transfer"
