# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Resumption across processes (SPEC.md 4.9, 4.11).

Run-once inside one instance is the easy half. The half an auditor asks about is the run that was
killed immediately after the transfer went out, and the process that picked the session up
afterwards.
"""

import asyncio
from collections import deque
from unittest.mock import create_autospec

from standard_agents.brokers.approvals.approval_broker import ApprovalDecision
from standard_agents.brokers.effects.file_effect_ledger_broker import FileEffectLedgerBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.sessions.file_session_broker import FileSessionBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


class _CountingTool(Tool):
    def __init__(self) -> None:
        self.execution_count = 0

    @property
    def name(self) -> str:
        return "wire_transfer"

    @property
    def description(self) -> str:
        return "Moves money."

    @property
    def parameters(self) -> str:
        return "{}"

    async def execute(self, input: str) -> str:
        self.execution_count += 1

        return "transfer complete"


async def _pending(effect):
    return ApprovalDecision.PENDING


async def _approved(effect):
    return ApprovalDecision.APPROVED


def _new_process(working_path, tool: _CountingTool, *replies: str) -> StandardAgent:
    """A separate instance each time, wired to the same folders: the closest a unit test comes to
    a different process, and the thing an in-memory ledger could never demonstrate."""
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = []

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    scripted_replies = deque(replies)

    async def generate(system_prompt: str, user_prompt: str) -> str:
        return scripted_replies.popleft() if scripted_replies else "FINAL: done"

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .tool(tool)
        .sessions(str(working_path / "sessions"))
        .use_effect_ledger(FileEffectLedgerBroker(str(working_path / "ledger")))
        .on_brain(generate))


async def test_should_not_repeat_an_effect_after_the_run_was_interrupted(tmp_path):
    # given: the first process pays the invoice and dies before it can answer
    tool = _CountingTool()

    await (_new_process(tmp_path, tool, "ACTION: wire_transfer: 10000")
        .max_turns(1)
        .process_prompt("pay the invoice", session_id="invoice-88"))

    assert tool.execution_count == 1

    # when: a second process picks the session up and the Brain proposes the same act
    resumed_tool = _CountingTool()

    actual_result = await (_new_process(
        tmp_path,
        resumed_tool,
        "ACTION: wire_transfer: 10000",
        "FINAL: already paid")
            .process_prompt("did that go through?", session_id="invoice-88"))

    # then: the resumed run kept the interrupted run's identity, so the effect is replayed
    assert resumed_tool.execution_count == 0
    assert actual_result == "already paid"


async def test_should_record_the_run_on_the_session_before_any_work(tmp_path):
    # given: a run cancelled before it starts, which never reaches the end of the loop and is
    # deliberately never written back as an answer
    tool = _CountingTool()
    cancellation = asyncio.Event()
    cancellation.set()

    await (_new_process(tmp_path, tool, "ACTION: wire_transfer: 10000")
        .process_prompt("pay the invoice", session_id="invoice-91", cancellation=cancellation))

    # when
    session_broker = FileSessionBroker(str(tmp_path / "sessions"))
    actual_session = await session_broker.select_session("invoice-91")

    # then: an identity recorded only on success is one the failure case can never use
    assert actual_session is not None
    assert actual_session.run_id != ""


async def test_should_perform_a_held_act_once_the_authority_approves_it(tmp_path):
    # given: the first process proposes the transfer and the authority has not answered yet
    tool = _CountingTool()

    held = await (_new_process(tmp_path, tool, "ACTION: wire_transfer: 10000")
        .require_approval("wire_transfer")
        .on_approval(_pending)
        .process_prompt("pay the invoice", session_id="invoice-95"))

    assert "waiting for approval" in held
    assert tool.execution_count == 0

    # when: the authority says yes, and a second process resumes the run
    resumed_tool = _CountingTool()

    actual_result = await (_new_process(
        tmp_path,
        resumed_tool,
        "ACTION: wire_transfer: 10000",
        "FINAL: paid")
            .require_approval("wire_transfer")
            .on_approval(_approved)
            .process_prompt("yes, approve it", session_id="invoice-95"))

    # then: a held act is one that still has to be able to happen; an approval that arrives
    # after the claim was left standing is an approval that can never be used
    assert resumed_tool.execution_count == 1
    assert actual_result == "paid"


async def test_should_finish_a_held_run_through_resume(tmp_path):
    # given: the authority has not answered, so the act is held
    tool = _CountingTool()

    await (_new_process(tmp_path, tool, "ACTION: wire_transfer: 10000")
        .require_approval("wire_transfer")
        .on_approval(_pending)
        .process_prompt("pay the invoice", session_id="invoice-97"))

    # when: a different process resumes the conversation with the authority's yes
    resumed_tool = _CountingTool()

    actual_result = await (_new_process(
        tmp_path,
        resumed_tool,
        "ACTION: wire_transfer: 10000",
        "FINAL: paid")
            .require_approval("wire_transfer")
            .on_approval(_approved)
            .resume(session_id="invoice-97", answer="yes, approve it"))

    # then: resuming asks nothing of the caller but the answer; the session holds the rest
    assert resumed_tool.execution_count == 1
    assert actual_result == "paid"


# SPEC.md 4.11 says a session carries `pending : AgentEffect?`: the act it was left waiting on.
# Storing only the question text means a resuming process cannot show a human WHAT they are
# approving, and an approval broker cannot check that the act it is now approving is the act that
# was held.
async def test_should_remember_the_act_the_session_is_waiting_on(tmp_path):
    # given
    tool = _CountingTool()

    await (_new_process(tmp_path, tool, "ACTION: wire_transfer: 10000")
        .require_approval("wire_transfer")
        .on_approval(_pending)
        .process_prompt("pay the invoice", session_id="invoice-99"))

    # when
    session_broker = FileSessionBroker(str(tmp_path / "sessions"))
    actual_session = await session_broker.select_session("invoice-99")

    # then: the held act travels with the session, so the authority is shown the act and not
    # merely told that something is waiting
    assert actual_session is not None
    assert actual_session.status == AgentStatus.AWAITING_APPROVAL
    assert actual_session.pending_effect is not None
    assert actual_session.pending_effect.tool_name == "wire_transfer"
    assert "10000" in actual_session.pending_effect.arguments
    assert actual_session.pending_effect.idempotency_key != ""
    assert actual_session.pending_effect.approval_required is True
