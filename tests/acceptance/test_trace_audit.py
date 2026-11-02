# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The decision log is machine-ingestible: one JSON object per trace event."""

from unittest.mock import create_autospec

from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.standard_agent import StandardAgent


async def _to_stream(*tokens: str):
    for token in tokens:
        yield token


def _streaming_generator_broker(*tokens: str) -> GeneratorBroker:
    generator_broker = create_autospec(GeneratorBroker, instance=True)

    # A loose Moq mock answers an unarranged bool with false: the broker does not put request
    # options on the wire.
    generator_broker.honors_request = False

    generator_broker.generate_stream.side_effect = (
        lambda system_prompt, user_prompt, inference=None: _to_stream(*tokens))

    return generator_broker


async def test_should_write_structured_json_audit_records(tmp_path):
    # given
    audit_path = str(tmp_path / "audit.jsonl")

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

    verifier_broker = create_autospec(VerifierBroker, instance=True)
    verifier_broker.verify.return_value = "1.0"

    mcp_broker = create_autospec(McpBroker, instance=True)

    # A loose Moq mock answers an unarranged list with an empty one: the server has no tools.
    mcp_broker.list_tools.return_value = []

    agent = (StandardAgent()
        .use_generator(_streaming_generator_broker("FINAL: 42"))
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .use_gate(classifier_broker)
        .use_judge(verifier_broker)
        .use_mcp(mcp_broker)
        .audit(audit_path))

    # when
    async for _ in agent.process_prompt_stream("what is the answer?"):
        pass

    with open(audit_path, encoding="utf-8") as file:
        audit = file.read()

    # then: one JSON object per trace event, machine-ingestible
    assert '"kind":"turn"' in audit
    assert '"kind":"process"' in audit
    assert '"kind":"outcome"' in audit
