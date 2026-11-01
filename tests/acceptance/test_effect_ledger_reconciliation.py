# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Found in the 2026-09-04 principal review (F-08): the ledger claimed an act before it ran and
recorded its outcome after, and the window between the two was a string.

A process that died, or a store that failed, after the transfer went out but before the outcome
was written left a claim with no outcome, and every later proposal of the same act read "effect
already in progress" as though it were the act's result, forever. The ledger now keeps typed
states with an owner and a lease; an earlier attempt with no usable outcome HOLDS the run with
the act as its pending effect, so a person can reconcile it against the world, and a reconciled
record is replayed the way any completed act is.
"""

import dataclasses
from datetime import timedelta

import pytest

from standard_agents.brokers.effects.effect_ledger_broker import EffectLedgerBroker
from standard_agents.brokers.effects.in_memory_effect_ledger_broker import (
    InMemoryEffectLedgerBroker)
from standard_agents.models.brokers.effects.effect_record import EffectRecord
from standard_agents.models.brokers.effects.effect_state import EffectState
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool

_SESSION_ID = "invoice-4471"
_PROPOSAL = "ACTION: wire_transfer: 10000"


class _CountingTool(Tool):
    def __init__(self, failure: Exception | None = None) -> None:
        self._failure = failure
        self.execution_count = 0

    @property
    def name(self) -> str:
        return "wire_transfer"

    @property
    def description(self) -> str:
        return "Moves money."

    async def execute(self, input: str) -> str:
        self.execution_count += 1

        if self._failure is not None:
            raise self._failure

        return "transfer complete"


class _FailingOutcomeLedger(EffectLedgerBroker):
    """The act happens; the note that it happened does not.

    A ledger whose first outcome write fails, over a store that otherwise works: the
    consistency window, made deterministic.
    """

    def __init__(self) -> None:
        self._store = InMemoryEffectLedgerBroker()
        self._failed_once = False

    async def insert_claim(self, claim: EffectRecord) -> bool:
        return await self._store.insert_claim(claim)

    async def select_record(self, idempotency_key: str) -> EffectRecord | None:
        return await self._store.select_record(idempotency_key)

    async def update_record(self, record: EffectRecord) -> None:
        if record.state is EffectState.COMPLETED and not self._failed_once:
            self._failed_once = True

            raise OSError("the ledger store is unavailable")

        await self._store.update_record(record)

    async def delete_record(self, idempotency_key: str) -> None:
        await self._store.delete_record(idempotency_key)


class _CapturingLedger(EffectLedgerBroker):
    """Keeps every claim the agent writes, so a test can read the lease it was written under."""

    def __init__(self) -> None:
        self._store = InMemoryEffectLedgerBroker()
        self.claims: list[EffectRecord] = []

    async def insert_claim(self, claim: EffectRecord) -> bool:
        self.claims.append(claim)

        return await self._store.insert_claim(claim)

    async def select_record(self, idempotency_key: str) -> EffectRecord | None:
        return await self._store.select_record(idempotency_key)

    async def update_record(self, record: EffectRecord) -> None:
        await self._store.update_record(record)

    async def delete_record(self, idempotency_key: str) -> None:
        await self._store.delete_record(idempotency_key)


@pytest.fixture
def new_process(tmp_path):
    """A separate instance each time over the same session folder and the same ledger: the
    closest a unit test comes to a different process."""
    sessions_path = str(tmp_path / "sessions")

    def create(ledger: EffectLedgerBroker, tool: _CountingTool, *replies: str) -> StandardAgent:
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
            return scripted_replies.pop(0) if scripted_replies else "FINAL: done"

        return (StandardAgent()
            .on_skills(select_skills)
            .on_memory(recall, remember)
            .on_knowledge(retrieve)
            .tool(tool)
            .sessions(sessions_path)
            .use_effect_ledger(ledger)
            .on_brain(generate))

    return create


def _request(prompt: str) -> PromptRequest:
    return PromptRequest(prompt=prompt, session_id=_SESSION_ID)


async def test_should_hold_a_repeated_act_whose_earlier_attempt_has_no_recorded_outcome(
        new_process):
    # given: the first process performs the transfer and the ledger loses the outcome
    ledger = _FailingOutcomeLedger()
    tool = _CountingTool()
    first_process = new_process(ledger, tool, _PROPOSAL).max_turns(1)

    with pytest.raises(Exception):
        await first_process.run(_request("pay the invoice"))

    assert tool.execution_count == 1

    # when: a second process picks the session up and the Brain proposes the same act
    resumed_tool = _CountingTool()

    actual_outcome = await new_process(ledger, resumed_tool, _PROPOSAL, "FINAL: paid").run(
        _request("did that go through?"))

    # then: not performed again, not replayed as if it had an outcome: held, with the act on
    # the outcome so a person can reconcile it against the world
    assert resumed_tool.execution_count == 0
    assert actual_outcome.status is AgentStatus.AWAITING_INPUT
    assert "reconcile" in actual_outcome.result
    assert actual_outcome.pending_effect is not None
    assert actual_outcome.pending_effect.tool_name == "wire_transfer"
    assert actual_outcome.pending_effect.idempotency_key != ""

    actual_record = await ledger.select_record(actual_outcome.pending_effect.idempotency_key)

    assert actual_record is not None
    assert actual_record.state is EffectState.IN_FLIGHT
    assert actual_record.tool_name == "wire_transfer"


async def test_should_replay_the_act_once_the_ledger_is_reconciled(new_process):
    # given: the same interrupted attempt, then a person reconciles the record
    ledger = _FailingOutcomeLedger()
    tool = _CountingTool()
    first_process = new_process(ledger, tool, _PROPOSAL).max_turns(1)

    with pytest.raises(Exception):
        await first_process.run(_request("pay the invoice"))

    held_outcome = await new_process(ledger, _CountingTool(), _PROPOSAL, "FINAL: paid").run(
        _request("did that go through?"))

    idempotency_key = held_outcome.pending_effect.idempotency_key
    unreconciled = await ledger.select_record(idempotency_key)

    await ledger.update_record(dataclasses.replace(
        unreconciled,
        state=EffectState.COMPLETED,
        outcome="transfer complete"))

    # when: a third process, same session, same proposal
    third_tool = _CountingTool()

    actual_outcome = await new_process(
        ledger, third_tool, _PROPOSAL, "FINAL: already paid").run(_request("and now?"))

    # then: replayed from the reconciled record, never performed again
    assert third_tool.execution_count == 0
    assert tool.execution_count == 1
    assert actual_outcome.status is AgentStatus.RESPONDED
    assert actual_outcome.result == "already paid"


async def test_should_claim_under_the_configured_lease(new_process):
    """The lease is how long an in-flight claim is presumed live; a deployment whose tools take
    longer than the default five minutes, or far less, says so once at composition."""
    # given
    ledger = _CapturingLedger()
    tool = _CountingTool()
    configured_lease = timedelta(seconds=30)

    agent = new_process(ledger, tool, _PROPOSAL, "FINAL: paid").effect_lease(configured_lease)

    # when
    actual_outcome = await agent.run(_request("pay the invoice"))

    # then: the act's claim was written for exactly the configured window
    assert actual_outcome.status is AgentStatus.RESPONDED
    assert tool.execution_count == 1

    [actual_claim] = ledger.claims

    assert actual_claim.lease_until - actual_claim.claimed_on == configured_lease
    assert actual_claim.tool_name == "wire_transfer"


async def test_should_record_a_failed_attempt_and_hold_its_repeat(new_process):
    # given: the tool itself fails, so whether the act happened is unknown
    ledger = InMemoryEffectLedgerBroker()
    failing_tool = _CountingTool(RuntimeError("the bank is offline"))
    first_process = new_process(ledger, failing_tool, _PROPOSAL).max_turns(1)

    with pytest.raises(Exception):
        await first_process.run(_request("pay the invoice"))

    assert failing_tool.execution_count == 1

    # when: the bank is back and the Brain proposes the same act on the same session
    healthy_tool = _CountingTool()

    actual_outcome = await new_process(ledger, healthy_tool, _PROPOSAL, "FINAL: paid").run(
        _request("try again"))

    # then: the failed attempt is on the record as failed, and the repeat is held, not run
    assert healthy_tool.execution_count == 0
    assert actual_outcome.status is AgentStatus.AWAITING_INPUT

    actual_record = await ledger.select_record(actual_outcome.pending_effect.idempotency_key)

    assert actual_record.state is EffectState.FAILED
