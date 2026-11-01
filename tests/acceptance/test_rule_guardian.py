# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import create_autospec

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.standard_agent import StandardAgent


async def _to_stream(*tokens: str):
    for token in tokens:
        await asyncio.sleep(0)

        yield token


def _streaming_generator(*tokens: str) -> GeneratorBroker:
    generator_broker = create_autospec(GeneratorBroker, instance=True)
    generator_broker.honors_request = False

    generator_broker.generate_stream.side_effect = (
        lambda system_prompt, user_prompt, inference=None: _to_stream(*tokens))

    return generator_broker


def _build_agent(generator_broker: GeneratorBroker) -> StandardAgent:
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = []
    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []
    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    # A loose Moq mock answers an unarranged list with an empty one: the server has no tools.
    mcp_broker = create_autospec(McpBroker, instance=True)
    mcp_broker.list_tools.return_value = []

    return (StandardAgent()
        .use_generator(generator_broker)
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .use_mcp(mcp_broker)
        .rule_gate("password"))


async def _drain(agent: StandardAgent, prompt: str) -> str:
    last = ""

    async for stream_event in agent.process_prompt_stream(prompt):
        last = stream_event.content

    return last


async def test_should_refuse_deterministically_when_rule_gate_matches():
    # given
    generator_broker = _streaming_generator("FINAL: your password is hunter2")
    agent = _build_agent(generator_broker)

    # when: a prompt that trips the rule
    await _drain(agent, "please reset my PASSWORD")

    # then: the brain is never reached; the gate stopped it deterministically
    assert generator_broker.generate_stream.mock_calls == []
