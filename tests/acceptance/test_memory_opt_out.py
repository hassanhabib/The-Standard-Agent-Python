# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Found in the 2026-09-04 principal review (F-05): every instance composed memory by default and
always registered the remember tool, so a host serving many callers from one agent let one
caller's remembered facts reach another caller's model, and let one caller poison memory for
everyone after. Memory stays the convenient default for a one-user agent; a deployment that
serves strangers says so, and the agent then recalls nothing and offers no way to store.
"""

from unittest.mock import call, create_autospec

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.standard_agent import StandardAgent

_REMEMBERED_FACT = "the user is Ada"


def _memory_holding(fact: str) -> MemoryBroker:
    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = [fact]

    return memory_broker


def _empty_knowledge() -> KnowledgeBroker:
    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    return knowledge_broker


async def _persona():
    return [Skill(name="persona", content="Your tools:\n{{tools}}")]


async def test_should_not_advertise_or_recall_memory_when_composed_without_memory():
    # given
    memory_broker = _memory_holding(_REMEMBERED_FACT)
    seen_by_brain = ""

    async def brain(system_prompt, user_prompt):
        nonlocal seen_by_brain
        seen_by_brain = system_prompt + "\n" + user_prompt

        return "FINAL: done"

    agent = (StandardAgent()
        .use_knowledge(_empty_knowledge())
        .on_skills(_persona)
        .use_memory(memory_broker)
        .without_memory()
        .on_brain(brain))

    # when
    await agent.process_prompt("hello")

    # then: nothing recalled, nothing offered, the store never asked
    assert _REMEMBERED_FACT not in seen_by_brain
    assert "remember" not in seen_by_brain
    assert memory_broker.select_memories.mock_calls == []


async def test_should_advertise_and_recall_memory_by_default():
    # given: the unamended one-user default
    memory_broker = _memory_holding(_REMEMBERED_FACT)
    seen_by_brain = ""

    async def brain(system_prompt, user_prompt):
        nonlocal seen_by_brain
        seen_by_brain = system_prompt + "\n" + user_prompt

        return "FINAL: done"

    agent = (StandardAgent()
        .use_knowledge(_empty_knowledge())
        .on_skills(_persona)
        .use_memory(memory_broker)
        .on_brain(brain))

    # when
    await agent.process_prompt("hello")

    # then
    assert _REMEMBERED_FACT in seen_by_brain
    assert "remember" in seen_by_brain
    assert memory_broker.select_memories.mock_calls == [call()]


# The document says it the same way code does: a document is the whole truth of a hosted agent,
# and a hosted agent that wants no memory needs one key to say so.
async def test_should_compose_without_memory_from_json_when_the_document_says_false():
    # given
    memory_broker = _memory_holding(_REMEMBERED_FACT)
    seen_by_brain = ""

    async def brain(system_prompt, user_prompt):
        nonlocal seen_by_brain
        seen_by_brain = system_prompt + "\n" + user_prompt

        return "FINAL: done"

    agent = (StandardAgent.from_json('{ "memory": false }')
        .use_knowledge(_empty_knowledge())
        .on_skills(_persona)
        .use_memory(memory_broker)
        .on_brain(brain))

    # when
    await agent.process_prompt("hello")

    # then
    assert _REMEMBERED_FACT not in seen_by_brain
    assert "remember" not in seen_by_brain
    assert memory_broker.select_memories.mock_calls == []
