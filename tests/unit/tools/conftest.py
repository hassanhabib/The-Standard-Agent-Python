# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

import pytest

from standard_agents.agent import Agent
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def nested_agent() -> Agent:
    return create_autospec(Agent, instance=True)


@pytest.fixture
def create_skill_broker():
    def create(*skills) -> SkillBroker:
        skill_broker = create_autospec(SkillBroker, instance=True)
        skill_broker.select_skills.return_value = list(skills)

        return skill_broker

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
