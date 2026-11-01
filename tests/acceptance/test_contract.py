# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The agent answers with a string, and that is the entire client contract. Every consumer wiring
# an agent into a workflow therefore writes a parser, which is exactly what the framework talked
# them out of doing everywhere else. Native tool calling gives structured input TO tools; the
# agent's own answer has always been prose.
#
# A schema check asks whether an answer is the right SHAPE, immediately beside the Judge asking
# whether it is good ENOUGH. Same moment, same kind of verdict, so it is a third guardian rather
# than a new concept, and a mismatch is a re-think, not a fault: it takes the Judge's revision
# path with the validation error as the reason the draft was rejected.

from unittest.mock import create_autospec

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.standard_agent import StandardAgent

INVOICE_SCHEMA = '{ "type": "object", "required": ["amount", "currency"] }'


def _agent_answering(*replies: str) -> StandardAgent:
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = []

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    asked = 0

    async def brain(system_prompt: str, user_prompt: str) -> str:
        nonlocal asked
        reply = replies[min(asked, len(replies) - 1)]
        asked += 1

        return reply

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .on_brain(brain))


async def test_should_return_the_answer_when_it_satisfies_the_contract():
    # given
    agent = (_agent_answering('FINAL: { "amount": 100, "currency": "USD" }')
        .contract(INVOICE_SCHEMA))

    # when
    actual_answer = await agent.process_prompt("what is owed")

    # then
    assert '"amount"' in actual_answer
    assert '"currency"' in actual_answer
