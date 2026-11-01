# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""A thrown failure appears in the human-readable trace; it does not vanish."""

import contextlib
from unittest.mock import create_autospec

from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.loggings.trace_verbosity import TraceVerbosity
from standard_agents.standard_agent import StandardAgent


async def test_should_write_failure_to_transcript_when_brain_throws(tmp_path):
    # given
    log_path = str(tmp_path / "trace.txt")

    generator_broker = create_autospec(GeneratorBroker, instance=True)

    # A loose Moq mock answers an unarranged bool with false: the broker does not put request
    # options on the wire.
    generator_broker.honors_request = False
    generator_broker.generate.side_effect = Exception("brain exploded")

    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = [Skill(content="Answer directly.")]

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    classifier_broker = create_autospec(ClassifierBroker, instance=True)
    classifier_broker.classify.return_value = "accept"

    # A loose Moq mock answers an unarranged string with null.
    classifier_broker.assess.return_value = None

    mcp_broker = create_autospec(McpBroker, instance=True)

    # A loose Moq mock answers an unarranged list with an empty one: the server has no tools.
    mcp_broker.list_tools.return_value = []

    agent = (StandardAgent()
        .use_generator(generator_broker)
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .use_gate(classifier_broker)
        .use_mcp(mcp_broker)
        .log_to(log_path, verbosity=TraceVerbosity.FULL))

    # when: the failure is expected; what is asserted is that it was traced
    with contextlib.suppress(Exception):
        await agent.process_prompt("what is the answer?")

    with open(log_path, encoding="utf-8") as file:
        transcript = file.read()

    # then: a thrown failure must appear in the audit trace, not vanish
    assert "ERROR" in transcript
