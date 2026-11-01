# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Found in the 2026-09-04 principal review (F-14): redact protected the model boundary, not the
logging boundary.

The decision log kept the raw prompt, the system prompt, the Brain's reply and every tool payload
in clear text, and an audit sink usually has broader access and a longer life than anything at
runtime. The decision log now records METADATA by default: what happened, who did it, when, and
how large and which payload it was (length and hash), never the payload itself. Payload capture
is a separate, deliberate opt-in, and when it is on, the configured redaction applies at the
audit boundary as it does at the model boundary.
"""

from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool

_CARD_NUMBER = "4111-1111-1111-1111"


class _EchoTool(Tool):
    """A tool the Brain calls with the card number, so a tool payload and a tool result both
    carry it."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes its input."

    async def execute(self, input: str) -> str:
        return f"echoed {input}"


@pytest.fixture
def audit_path(tmp_path):
    return str(tmp_path / "audit-policy.jsonl")


def _bare_shell() -> StandardAgent:
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = []

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker))


@pytest.fixture
def echoing_agent(audit_path):
    # A Brain that echoes the card number back, so the reply carries it too.
    turn = 0

    async def brain(system_prompt, user_prompt):
        nonlocal turn
        turn += 1

        if turn == 1:
            return f"ACTION: echo: {_CARD_NUMBER}"

        return f"FINAL: noted {_CARD_NUMBER}"

    return (_bare_shell()
        .tool(_EchoTool())
        .audit(audit_path)
        .on_brain(brain))


def _read_decision_log(path: str) -> str:
    # The sink is JSON lines, and the serializer escapes an apostrophe as a ' sequence; read
    # it the way a reader would, with the escape undone, so an assertion can name a tool.
    with open(path, encoding="utf-8") as file:
        return file.read().replace("\\u0027", "'")


async def test_should_withhold_payloads_from_the_decision_log_by_default(
        echoing_agent,
        audit_path):
    # given
    agent = echoing_agent

    # when
    answer = await agent.process_prompt(f"my card is {_CARD_NUMBER}")
    decision_log = _read_decision_log(audit_path)

    # then: the run happened and the answer carried the number; the log did not
    assert _CARD_NUMBER in answer
    assert _CARD_NUMBER not in decision_log

    # and what happened is still on the record: the events, and the shape of the payloads
    assert "Received prompt" in decision_log
    assert "Brain replied" in decision_log
    assert "Tool 'echo' input" in decision_log
    assert "Tool 'echo' output" in decision_log
    assert '"payloadLength":' in decision_log
    assert '"payloadHash":' in decision_log
