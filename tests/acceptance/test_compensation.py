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
