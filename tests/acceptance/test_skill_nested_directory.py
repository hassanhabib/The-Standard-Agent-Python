# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import create_autospec

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.standard_agent import StandardAgent


async def test_should_load_skill_from_nested_directory_and_strip_frontmatter(tmp_path):
    # given: a skill nested one folder deep, with YAML frontmatter
    root = tmp_path / "skills"
    nested = root / "the-standard-skill"
    nested.mkdir(parents=True)

    (nested / "SKILL.md").write_text(
        "---\nname: the-standard-skill\ndescription: does the standard thing\n---\n"
        "Always answer in a haiku.",
        encoding="utf-8")

    captured_system_prompt = ""

    async def generate(system_prompt, user_prompt, *, inference=None):
        nonlocal captured_system_prompt
        captured_system_prompt = system_prompt

        return "FINAL: ok"

    generator_broker = create_autospec(GeneratorBroker, instance=True)
    generator_broker.honors_request = False
    generator_broker.generate.side_effect = generate

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []
    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    # A loose Moq mock answers an unarranged list with an empty one: the server has no tools.
    mcp_broker = create_autospec(McpBroker, instance=True)
    mcp_broker.list_tools.return_value = []

    agent = (StandardAgent()
        .use_generator(generator_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .use_mcp(mcp_broker)
        .skills(str(root)))

    # when
    await agent.process_prompt("hello")

    # then: the nested skill's body reached the brain, frontmatter stripped
    assert "Always answer in a haiku." in captured_system_prompt
    assert "description: does the standard thing" not in captured_system_prompt
