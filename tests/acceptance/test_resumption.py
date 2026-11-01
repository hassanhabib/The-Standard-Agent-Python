# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Resumption across processes (SPEC.md 4.9, 4.11).

Run-once inside one instance is the easy half. The half an auditor asks about is the run that was
killed immediately after the transfer went out, and the process that picked the session up
afterwards.
"""

from collections import deque
from unittest.mock import create_autospec

from standard_agents.brokers.effects.file_effect_ledger_broker import FileEffectLedgerBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
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
