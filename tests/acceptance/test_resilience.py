# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Cancellation, retry and budget end to end (SPEC.md 4.10).

An agent that cannot be stopped, cannot survive a transient failure, and cannot say what it
spent is not something an enterprise can operate, however correct each decision is.
"""

import asyncio
from datetime import timedelta
from http import HTTPStatus

from restfulsense import HttpRequestException
from standard_agents.standard_agent import StandardAgent


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


def _agent_with_native_brain_that_always_fails() -> StandardAgent:
    async def brain(messages, tools):
        raise HttpRequestException(
            "the native provider is down",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE)

    return (StandardAgent()
        .on_skills(_select_no_skills)
        .on_memory(_recall_nothing, _remember_nothing)
        .on_knowledge(_retrieve_nothing)
        .on_native_brain(brain))


async def test_should_fall_back_on_the_native_protocol_when_the_circuit_opens():
    """Found in the 2026-09-04 principal review (F-07): the fallback broker cast the configured
    string answer to whatever T the caller asked for. On the text protocol T is a string and the
    cast is free; on the native protocol T is GenerationResult, so the moment the circuit
    opened, exactly when the control is supposed to work, the fallback threw instead of
    degrading. A control that holds on one protocol and not the other is a control a caller can
    step around by changing configuration."""
    # given
    async def fallback():
        return "Answering from the standby model."

    agent = _agent_with_native_brain_that_always_fails().fallback(
        fallback=fallback,
        failures_before_open=1)

    # when
    actual_answer = await agent.process_prompt("what is the answer")

    # then
    assert actual_answer == "Answering from the standby model."


async def test_should_stop_the_loop_when_cancelled():
    # given: a Brain that would loop forever through tool calls
    cancellation = asyncio.Event()
    brain_calls = 0

    def reply_for_turn(turn):
        nonlocal brain_calls
        brain_calls += 1
        cancellation.set()

        return "ACTION: nonexistent_tool: keep going"

    agent = _agent_that_loops(reply_for_turn)

    # when
    actual_result = await agent.process_prompt("loop forever", cancellation=cancellation)

    # then: stopped at the next turn boundary, and said so rather than answering
    assert "cancelled" in actual_result
    assert brain_calls == 1


async def test_should_not_report_cancellation_as_an_answer():
    # given
    cancellation = asyncio.Event()
    cancellation.set()

    agent = _agent_that_loops(lambda turn: "FINAL: 42")

    # when
    actual_result = await agent.process_prompt("what is the answer?", cancellation=cancellation)

    # then: a cancelled run's result is not an answer
    assert actual_result != "42"
    assert "cancelled" in actual_result


async def test_should_stop_the_loop_when_the_time_budget_is_exhausted():
    # given: every turn asks for a tool that does not exist, so the loop keeps going
    agent = (_agent_that_loops(lambda turn: "ACTION: nonexistent_tool: keep going")
        .max_turns(50)
        .budget(max_wall_clock=timedelta(0)))

    # when
    actual_result = await agent.process_prompt("loop forever")

    # then: exhaustion is distinguishable from a refusal
    assert "time budget" in actual_result
    assert "not able to help" not in actual_result


async def test_should_run_unbounded_when_no_budget_is_configured():
    # given
    agent = _agent_that_loops(lambda turn: "FINAL: 42")

    # when
    actual_result = await agent.process_prompt("what is the answer?")

    # then: absent a budget the agent behaves exactly as it did
    assert actual_result == "42"
