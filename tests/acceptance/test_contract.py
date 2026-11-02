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
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
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


# The whole point: a shape violation is a revision signal, not an exception and not a silent pass.
# The model is told what was wrong and asked again within the turn budget.
async def test_should_revise_when_the_answer_does_not_satisfy_the_contract():
    # given: prose first, then the shape that was asked for
    agent = (_agent_answering(
            "FINAL: The amount is one hundred US dollars.",
            'FINAL: { "amount": 100, "currency": "USD" }')
        .contract(INVOICE_SCHEMA)
        .max_turns(5))

    # when
    actual_answer = await agent.process_prompt("what is owed")

    # then: a draft that does not satisfy the contract is re-thought, and the second draft is
    # the one the caller receives
    assert '"amount"' in actual_answer
    assert "one hundred US dollars" not in actual_answer


# A model that never produces the shape must fail the way every other exhausted control fails: a
# graceful refusal, distinguishable from an answer. Never an exception, and never prose handed
# back as though it had satisfied a schema it did not.
async def test_should_refuse_when_the_contract_is_never_satisfied():
    # given
    agent = (_agent_answering("FINAL: The amount is one hundred US dollars.")
        .contract(INVOICE_SCHEMA)
        .max_turns(3))

    # when
    actual_answer = await agent.process_prompt("what is owed")

    # then: prose handed back unchanged is the failure this exists to prevent, since a caller
    # parsing the result would have no way to tell it never matched; and an exhausted contract
    # refuses gracefully, the same as an exhausted revision budget, rather than throwing or
    # returning nothing
    assert actual_answer != "The amount is one hundred US dollars."
    assert actual_answer.strip() != ""


# Found in the 2026-08-23 sweep: check_shape had exactly one call site, think, so the identical
# prose the batched path re-thinks streamed out as the answer. A guardian a caller can step around
# by changing method is not a guardian (SPEC.md 7.6).
async def test_should_enforce_the_contract_on_the_streamed_path():
    # given: the same drafts as the batched revision test above
    agent = (_agent_answering(
            "FINAL: The amount is one hundred US dollars.",
            'FINAL: { "amount": 100, "currency": "USD" }')
        .contract(INVOICE_SCHEMA)
        .max_turns(5))

    # when
    responses = [
        stream_event.content
        async for stream_event in agent.process_prompt_stream("what is owed")
        if stream_event.type is AgentStreamEventType.RESPONSE]

    # then: the shape that satisfied the contract, and never the prose that did not; a draft the
    # contract rejects on the batched path must not be delivered by switching to the streamed one
    streamed_answer = "".join(responses)

    assert '"amount"' in streamed_answer
    assert "one hundred US dollars" not in streamed_answer


# Wide open by default: an agent given no contract is not constrained by having become checkable.
# Same rule as counting versus blocking in the budget.
async def test_should_not_constrain_an_agent_given_no_contract():
    # given
    agent = _agent_answering("FINAL: The amount is one hundred US dollars.")

    # when
    actual_answer = await agent.process_prompt("what is owed")

    # then
    assert actual_answer == "The amount is one hundred US dollars."
