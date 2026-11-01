# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Say so in the trace (docs/per-request-inference.md 4.3).

The framework already narrates its guardian decisions on the stated principle that a rejection
the trace does not explain is a turn nobody can account for. A caller whose schema was
discarded, whose passthrough key was stripped, or whose options quietly degraded to
guardian-only deserves the same courtesy.
"""

from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.standard_agent import StandardAgent


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "trace.txt")


@pytest.fixture
def agent_with(log_path):
    def create(brain) -> StandardAgent:
        skill_broker = create_autospec(SkillBroker, instance=True)
        skill_broker.select_skills.return_value = [Skill(content="You are a helpful agent.")]

        memory_broker = create_autospec(MemoryBroker, instance=True)
        memory_broker.select_memories.return_value = []

        knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
        knowledge_broker.select_knowledge.return_value = []

        return (StandardAgent()
            .use_skills(skill_broker)
            .use_memory(memory_broker)
            .use_knowledge(knowledge_broker)
            .log_to(log_path)
            .on_brain(brain))

    return create


def _read_trace(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


async def test_should_announce_a_discarded_request_schema(agent_with, log_path):
    # given: a configured Contract, and a caller who sent a schema anyway
    async def brain(system_prompt, user_prompt):
        return 'FINAL: {"city":"Paris"}'

    agent = (agent_with(brain)
        .contract('{"type":"object","required":["city"]}'))

    request = PromptRequest(
        prompt="capital of France, as JSON",
        response_schema_json='{"type":"object","required":["name"]}')

    # when
    await agent.process_prompt(request)

    # then: the caller got a differently-shaped answer, and the trace says why
    trace = _read_trace(log_path)
    assert "request schema discarded" in trace


async def _answering_ok(system_prompt, user_prompt):
    return "FINAL: ok"


async def test_should_announce_a_stripped_core_owned_key(agent_with, log_path):
    # given: a passthrough trying to raise max_tokens past what precedence resolved
    agent = agent_with(_answering_ok)

    request = PromptRequest(
        prompt="hello",
        provider_options_json='{"max_tokens": 999999, "grammar": "root ::= object"}')

    # when
    await agent.process_prompt(request)

    # then
    trace = _read_trace(log_path)
    assert "max_tokens" in trace
    assert "stripped" in trace
