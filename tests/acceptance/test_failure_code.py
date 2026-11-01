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


async def test_should_report_an_exhausted_budget_as_budget_exhausted():
    # given
    agent = (_agent_that_loops(lambda turn: "ACTION: nonexistent_tool: keep going")
        .max_turns(50)
        .budget(max_wall_clock=timedelta(0)))

    # when
    outcome = await agent.run("loop forever")

    # then
    assert outcome.status is AgentStatus.FAILED
    assert outcome.failure is not None
    assert outcome.failure.code == AgentFailureCodes.BUDGET_EXHAUSTED
    assert outcome.failure.message == outcome.result


async def test_should_report_a_run_out_of_turns_as_turns_exhausted():
    # given
    agent = _agent_that_loops(lambda turn: "ACTION: nonexistent_tool: keep going").max_turns(2)

    # when
    outcome = await agent.run("loop forever")

    # then: still WORKING, because the run stopped mid-work, and now with the code that says so
    assert outcome.status is AgentStatus.WORKING
    assert outcome.failure is not None
    assert outcome.failure.code == AgentFailureCodes.TURNS_EXHAUSTED
    assert outcome.failure.message == outcome.result


async def test_should_stop_a_run_going_in_circles():
    # given: watched live, twice: a model asked for the same thing eleven more times with the
    # note in front of it, and a turn cap of sixty-four is sixty turns of the same question
    # (SPEC.md 4.10, v1.14). The act runs once; every ask after it is a replay.
    tool = _CountingTool()

    agent = (_agent_that_loops(lambda turn: "ACTION: calculator: 1 + 1")
        .tool(tool)
        .max_turns(20)
        .identical_call_limit(3))

    # when
    outcome = await agent.run("add one and one")

    # then: asked, replayed, told, and then told the run is over: not a refusal and not an
    # answer
    assert tool.calls == 1
    assert outcome.status is AgentStatus.FAILED
    assert outcome.failure is not None
    assert outcome.failure.code == AgentFailureCodes.GOING_IN_CIRCLES
    assert outcome.failure.message == outcome.result


class _CountingTool(Tool):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates arithmetic."

    async def execute(self, input: str) -> str:
        self.calls += 1

        return "2"


async def test_should_carry_no_failure_on_a_run_that_answered():
    # given
    agent = _agent_that_loops(lambda turn: "FINAL: 42")

    # when
    outcome = await agent.run("what is the answer?")

    # then: an answer is not a stop without an answer, and must never look like one
    assert outcome.status is AgentStatus.RESPONDED
    assert outcome.failure is None
