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
