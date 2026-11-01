# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Why a run stopped without an answer, as a code (SPEC.md 3.6, v1.14).

A status says that a run did not answer; it does not say why, and a caller cannot tell "retry
this" from "change the prompt" from a sentence it would have to parse. These pin each stop's
code from the outside, through run, because that is where a caller reads it.
"""

import asyncio
from datetime import timedelta

from standard_agents.models.clients.agents.agent_failure_category import AgentFailureCategory
from standard_agents.models.clients.agents.agent_failure_codes import AgentFailureCodes
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


async def _select_no_skills():
    return []


async def _recall_nothing():
    return []


async def _remember_nothing(memory):
    return None


async def _retrieve_nothing(query):
    return []


def _agent_that_loops(reply_for_turn) -> StandardAgent:
    turn = 0

    async def brain(system_prompt, user_prompt):
        nonlocal turn
        reply = reply_for_turn(turn)
        turn += 1

        return reply

    return (StandardAgent()
        .on_skills(_select_no_skills)
        .on_memory(_recall_nothing, _remember_nothing)
        .on_knowledge(_retrieve_nothing)
        .on_brain(brain))


async def test_should_report_a_cancelled_run_as_cancelled():
    # given
    cancellation = asyncio.Event()

    def reply_for_turn(turn):
        cancellation.set()

        return "ACTION: nonexistent_tool: keep going"

    agent = _agent_that_loops(reply_for_turn)

    # when
    outcome = await agent.run("loop forever", cancellation=cancellation)

    # then
    assert outcome.status is AgentStatus.FAILED
    assert outcome.failure is not None
    assert outcome.failure.code == AgentFailureCodes.CANCELLED
    assert outcome.failure.category is AgentFailureCategory.SERVICE
    assert outcome.failure.message == outcome.result
