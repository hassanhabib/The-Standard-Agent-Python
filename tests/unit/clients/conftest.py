# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


@pytest.fixture
def create_skill_broker():
    def create(*skills: Skill) -> SkillBroker:
        skill_broker = create_autospec(SkillBroker, instance=True)
        skill_broker.select_skills.return_value = list(skills)

        return skill_broker

    return create


@pytest.fixture
def create_generator_broker():
    """A generator whose replies are scripted: one fixed reply, or one per call in order."""

    def create(*replies: str) -> GeneratorBroker:
        generator_broker = create_autospec(GeneratorBroker, instance=True)

        # A loose Moq mock answers an unarranged bool with false: the broker does not put
        # request options on the wire.
        generator_broker.honors_request = False

        if len(replies) == 1:
            generator_broker.generate.return_value = replies[0]
        else:
            generator_broker.generate.side_effect = list(replies)

        return generator_broker

    return create


@pytest.fixture
def empty_memory_broker() -> MemoryBroker:
    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    return memory_broker


@pytest.fixture
def empty_knowledge_broker() -> KnowledgeBroker:
    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    return knowledge_broker


@pytest.fixture
def allowing_classifier_broker() -> ClassifierBroker:
    classifier_broker = create_autospec(ClassifierBroker, instance=True)
    classifier_broker.classify.return_value = "allow"

    # A loose Moq mock answers an unarranged string with null.
    classifier_broker.assess.return_value = None

    return classifier_broker


@pytest.fixture
def passing_verifier_broker() -> VerifierBroker:
    verifier_broker = create_autospec(VerifierBroker, instance=True)
    verifier_broker.verify.return_value = "1.0"

    return verifier_broker


@pytest.fixture
def create_mcp_broker():
    def create() -> McpBroker:
        mcp_broker = create_autospec(McpBroker, instance=True)

        # A loose Moq mock answers an unarranged list with an empty one: the server has no
        # tools.
        mcp_broker.list_tools.return_value = []

        return mcp_broker

    return create


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def create_fully_stubbed_agent(
        create_skill_broker,
        create_generator_broker,
        empty_memory_broker,
        empty_knowledge_broker,
        allowing_classifier_broker,
        passing_verifier_broker,
        create_mcp_broker,
        logging_broker):

    def create(brain_reply: str) -> StandardAgent:
        return (StandardAgent()
            .use_skills(create_skill_broker(Skill(content="you are an agent")))
            .use_generator(create_generator_broker(brain_reply))
            .use_memory(empty_memory_broker)
            .use_knowledge(empty_knowledge_broker)
            .use_gate(allowing_classifier_broker)
            .use_judge(passing_verifier_broker)
            .use_mcp(create_mcp_broker())
            .use_logging(logging_broker))

    return create


@pytest.fixture
def create_tool():
    """A tool as a loose Moq mock of it answers: what is arranged, and null for the rest."""

    def create(name: str, description: str | None = None, parameters: str | None = None) -> Tool:
        tool = create_autospec(Tool, instance=True)
        tool.name = name
        tool.description = description
        tool.parameters = parameters
        tool.risk = RiskLevel.SAFE
        tool.narration_starting = None
        tool.narration_observed = None
        tool.scope_of.return_value = None

        return tool

    return create
