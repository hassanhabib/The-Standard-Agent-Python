# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Compensation end to end (SPEC.md 4.9).

Run-once makes an effect safe to PROPOSE twice; these pin what happens to the effects that
cannot be made idempotent at all: the ones a bank asks about when the run dies halfway through a
two-step payment.
"""

from collections.abc import Iterable

from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision)
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


class _ReversibleTool(Tool):
    """A tool that knows how to undo itself, and records the order it was called in."""

    def __init__(self, name: str, ledger: list[str]) -> None:
        self._name = name
        self._ledger = ledger

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Performs {self._name}."

    async def execute(self, input: str) -> str:
        self._ledger.append(f"do:{self._name}")

        return f"{self._name}-receipt"

    async def compensate(self, input: str, outcome: str) -> str | None:
        self._ledger.append(f"undo:{self._name}")

        return f"reversed {outcome}"


class _IrreversibleTool(Tool):
    """A tool that cannot be undone: it leaves the default, which says so."""

    def __init__(self, name: str, ledger: list[str]) -> None:
        self._name = name
        self._ledger = ledger

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Performs {self._name}."

    async def execute(self, input: str) -> str:
        self._ledger.append(f"do:{self._name}")

        return f"{self._name}-sent"


def _agent_that_runs(tools: Iterable[Tool], *replies: str) -> StandardAgent:
    scripted_replies = list(replies)

    async def select_skills():
        return []

    async def recall():
        return []

    async def remember(memory):
        return None

    async def retrieve(query):
        return []

    async def generate(system_prompt, user_prompt):
        return scripted_replies.pop(0) if scripted_replies else "ACTION: book_flight: LHR-JFK"

    return (StandardAgent()
        .on_skills(select_skills)
        .on_memory(recall, remember)
        .on_knowledge(retrieve)
        .tools(tools)
        .on_brain(generate))


async def test_should_unwind_performed_effects_in_reverse_order_when_the_run_fails():
    # given: the run books, then charges, then runs out of turns without ever answering
    ledger: list[str] = []

    agent = (_agent_that_runs(
            [_ReversibleTool("book_flight", ledger), _ReversibleTool("charge_card", ledger)],
            "ACTION: book_flight: LHR-JFK",
            "ACTION: charge_card: 480.00")
        .max_turns(2)
        .compensate_on_failure())

    # when
    actual_result = await agent.process_prompt("book me a flight")

    # then: the charge is reversed before the booking it paid for
    assert ledger == ["do:book_flight", "do:charge_card", "undo:charge_card", "undo:book_flight"]
    assert "Unwound 2 of 2 effects." in actual_result


async def test_should_report_effects_that_could_not_be_undone():
    # given: one tool knows how to reverse itself and one does not
    ledger: list[str] = []

    agent = (_agent_that_runs(
            [_ReversibleTool("book_flight", ledger), _IrreversibleTool("send_email", ledger)],
            "ACTION: book_flight: LHR-JFK",
            "ACTION: send_email: your ticket is confirmed")
        .max_turns(2)
        .compensate_on_failure())

    # when
    actual_result = await agent.process_prompt("book me a flight")

    # then: silence is not reversal; the caller is told what stands
    assert "Unwound 1 of 2 effects." in actual_result
    assert "'send_email' could not be undone; the effect stands." in actual_result
    assert "undo:send_email" not in ledger


async def test_should_not_compensate_effects_that_were_never_performed():
    # given: policy denies the charge, so only the booking was ever performed
    ledger: list[str] = []

    async def authorize(effect):
        return (
            AuthorizationDecision.deny("card charges are not permitted")
            if effect.tool_name == "charge_card"
            else AuthorizationDecision.allow())

    agent = (_agent_that_runs(
            [_ReversibleTool("book_flight", ledger), _ReversibleTool("charge_card", ledger)],
            "ACTION: book_flight: LHR-JFK",
            "ACTION: charge_card: 480.00")
        .max_turns(2)
        .compensate_on_failure()
        .on_policy(authorize))

    # when
    actual_result = await agent.process_prompt("book me a flight")

    # then: a denied effect was never performed, so there is nothing of it to undo
    assert ledger == ["do:book_flight", "undo:book_flight"]
    assert "Unwound 1 of 1 effects." in actual_result


async def test_should_not_unwind_a_run_that_delivered_an_answer():
    # given: the run performs an effect and then answers, which is a completed run
    ledger: list[str] = []

    agent = (_agent_that_runs(
            [_ReversibleTool("book_flight", ledger)],
            "ACTION: book_flight: LHR-JFK",
            "FINAL: booked")
        .compensate_on_failure())

    # when
    actual_result = await agent.process_prompt("book me a flight")

    # then
    assert actual_result == "booked"
    assert ledger == ["do:book_flight"]


async def test_should_leave_effects_standing_when_compensation_is_not_configured():
    # given: compensation is off, which is the default
    ledger: list[str] = []

    agent = _agent_that_runs(
            [_ReversibleTool("book_flight", ledger)],
            "ACTION: book_flight: LHR-JFK").max_turns(1)

    # when
    await agent.process_prompt("book me a flight")

    # then: behavior is exactly as if the section did not exist
    assert ledger == ["do:book_flight"]


async def test_should_unwind_the_remaining_effects_when_one_compensation_fails():
    # given: undoing the charge throws; the booking behind it must still be unwound
    ledger: list[str] = []

    agent = (_agent_that_runs(
            [_ReversibleTool("book_flight", ledger), _ThrowingTool("charge_card", ledger)],
            "ACTION: book_flight: LHR-JFK",
            "ACTION: charge_card: 480.00")
        .max_turns(2)
        .compensate_on_failure())

    # when
    actual_result = await agent.process_prompt("book me a flight")

    # then: abandoning the rest would leave more standing, not less
    assert "undo:book_flight" in ledger
    assert "Unwound 1 of 2 effects." in actual_result
    assert "'charge_card' could not be undone; the effect stands." in actual_result


class _ThrowingTool(Tool):
    """A tool whose undo fails: the reversal itself is an act against the world, and acts
    fail."""

    def __init__(self, name: str, ledger: list[str]) -> None:
        self._name = name
        self._ledger = ledger

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Performs {self._name}."

    async def execute(self, input: str) -> str:
        self._ledger.append(f"do:{self._name}")

        return f"{self._name}-receipt"

    async def compensate(self, input: str, outcome: str) -> str | None:
        raise RuntimeError("the reversal window has closed")
