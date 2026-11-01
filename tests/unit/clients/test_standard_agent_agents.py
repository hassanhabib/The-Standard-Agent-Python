# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The fleet: registered agents materialize as tools at composition. That one decision buys
# everything the framework already knows how to do (the advertisement opt-in, the perimeter, the
# audit, cancellation across the seam) without a second code path for "agent" beside "tool". A
# handoff is an act, and the same door governs every act.

import itertools

from standard_agents.models.brokers.agents.registered_agent import RegisteredAgent
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent


def registry_of(*registered_agents):
    async def select_agents():
        return list(registered_agents)

    return select_agents


async def test_should_hand_off_to_a_registered_agent(empty_memory_broker, empty_knowledge_broker):
    # given: a registered specialist that captures what it was actually handed.
    inner_received = []

    async def billing_brain(system_prompt, user_prompt):
        inner_received.append(user_prompt)

        return "FINAL: the refund is booked"

    billing_agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_brain(billing_brain))

    turns = itertools.count(1)

    async def outer_brain(system_prompt, user_prompt):
        return (
            "ACTION: billing: refund order 7741" if next(turns) == 1
            else "FINAL: done, billing booked the refund.")

    outer_agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_agents(registry_of(
            RegisteredAgent("billing", "Handles refunds and invoices.", billing_agent)))
        .on_brain(outer_brain))

    # when
    answer = await outer_agent.process_prompt("please refund my last order, number 7741")

    # then: the handoff was grounded: the task the outer brain wrote AND the user's original ask,
    # which is the default sharing ruling (task + just enough context).
    assert "refund order 7741" in inner_received[-1]
    assert "please refund my last order, number 7741" in inner_received[-1]
    assert "billing booked the refund" in answer


async def select_concierge():
    return [Skill(name="concierge", content="Hand work to whoever does it best.\n\n{{tools}}")]


async def test_should_advertise_registered_agents_to_the_brain(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: a registry whose agent carries a description, which is the advertisement opt-in a
    # tool's description already is, surfaced where every advertisement is surfaced: a skill's
    # {{tools}} marker.
    async def specialist_brain(system_prompt, user_prompt):
        return "FINAL: ok"

    specialist = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_brain(specialist_brain))

    outer_saw = []

    async def outer_brain(system_prompt, user_prompt):
        outer_saw.append(system_prompt)

        return "FINAL: nothing to do"

    outer_agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_skills(select_concierge)
        .on_agents(registry_of(
            RegisteredAgent("billing", "Handles refunds and invoices.", specialist)))
        .on_brain(outer_brain))

    # when
    await outer_agent.process_prompt("hello")

    # then: the brain can only hand off to an agent it was told exists.
    assert "billing" in outer_saw[-1]
    assert "Handles refunds and invoices." in outer_saw[-1]


# The third flavor of a handoff: TRANSFER. Where a sub-agent call brings the answer BACK for the
# outer brain to synthesize, a transfer hands the whole run over: the specialist's answer IS the
# answer, delivered as delivered, and the outer brain never rewrites it.
async def test_should_transfer_the_run_to_a_registered_agent(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: a specialist that answers, and an outer brain that recognizes the whole prompt
    # belongs to it.
    inner_received = []

    async def billing_brain(system_prompt, user_prompt):
        inner_received.append(user_prompt)

        return "FINAL: the refund is booked"

    billing_agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_brain(billing_brain))

    outer_turns = []

    async def outer_brain(system_prompt, user_prompt):
        outer_turns.append(user_prompt)

        return "TRANSFER: billing"

    outer_agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_agents(registry_of(
            RegisteredAgent("billing", "Handles refunds and invoices.", billing_agent)))
        .on_brain(outer_brain))

    # when
    answer = await outer_agent.process_prompt("please refund my last order, number 7741")

    # then: the specialist's words, verbatim; one outer turn, no synthesis turn; and the
    # specialist was grounded in the user's actual ask.
    assert answer == "the refund is booked"
    assert len(outer_turns) == 1
    assert "please refund my last order, number 7741" in inner_received[-1]


# A transfer that does not deliver is an observation, not an answer. The specialist's own
# controls can refuse or hold, and the outer loop then keeps working the task instead of
# presenting the refusal as the user's answer.
async def test_should_keep_working_when_a_transfer_does_not_deliver(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: a specialist whose own gate refuses everything about refunds.
    async def strict_brain(system_prompt, user_prompt):
        return "FINAL: should never be reached"

    strict_agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .rule_gate("refund")
        .on_brain(strict_brain))

    turns = itertools.count(1)

    async def outer_brain(system_prompt, user_prompt):
        return (
            "TRANSFER: billing" if next(turns) == 1
            else "FINAL: billing could not take this; here is what I can do instead.")

    outer_agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_agents(registry_of(
            RegisteredAgent("billing", "Handles refunds and invoices.", strict_agent)))
        .on_brain(outer_brain))

    # when
    outcome = await outer_agent.run("please refund order 7741")

    # then: the outer brain saw the failed transfer and answered itself.
    assert outcome.status is AgentStatus.RESPONDED
    assert "here is what I can do instead" in outcome.result


# The fleet is data like everything else: an "agents" entry is either a folder of agent documents
# (a path) or an agent document riding inline, identity included, because the document IS the
# agent. A form that can post JSON can post a fleet.
async def test_should_compose_a_fleet_from_json(empty_memory_broker, empty_knowledge_broker):
    # given
    fleet = """
    {
      "agents": [
        { "name": "billing", "description": "Handles refunds and invoices.", "maxTurns": 2 }
      ]
    }
    """

    outer_saw = []

    async def outer_brain(system_prompt, user_prompt):
        outer_saw.append(system_prompt)

        return "FINAL: nothing to do"

    outer_agent = (StandardAgent.from_json(fleet)
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_skills(select_concierge)
        .on_brain(outer_brain))

    # when
    await outer_agent.process_prompt("hello")

    # then: the document's fleet member is advertised exactly as a registered agent is.
    assert "billing" in outer_saw[-1]
    assert "Handles refunds and invoices." in outer_saw[-1]
