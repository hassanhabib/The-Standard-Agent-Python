# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Handoff sharing is a template (SPEC 6.1): {input} is what the outer model wrote, {prompt} is
# what the user originally asked. The grounded default carries both (the task, and just enough
# context to do it), and a custom template decides exactly what crosses, which is the whole
# configurability of a handoff.

import itertools

from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.agent_tool import AgentTool


async def test_should_ground_handoff_with_the_original_prompt(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: an inner agent that captures what it was actually handed.
    inner_received = []

    async def inner_brain(system_prompt, user_prompt):
        inner_received.append(user_prompt)

        return "FINAL: the refund is booked"

    inner_agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_brain(inner_brain))

    handoff_tool = AgentTool(
        name="billing",
        agent=inner_agent,
        handoff="The user asked: {prompt}\n\nYour task: {input}",
        description="handles refunds and invoices")

    turns = itertools.count(1)

    async def outer_brain(system_prompt, user_prompt):
        return (
            "ACTION: billing: refund order 7741" if next(turns) == 1
            else "FINAL: done, billing booked the refund.")

    outer_agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .tool(handoff_tool)
        .on_brain(outer_brain))

    # when
    await outer_agent.process_prompt("please refund my last order, number 7741")

    # then: the sub-agent received the task AND the user's original ask, not the task alone.
    assert "refund order 7741" in inner_received[-1]
    assert "please refund my last order, number 7741" in inner_received[-1]
