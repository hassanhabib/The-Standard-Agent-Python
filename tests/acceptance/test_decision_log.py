# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The decision log end to end, through the Local mode: a file (SPEC.md 4.7).

The regression these pin is the one the enterprise plan opens on: the audit file used to be
truncated at the start of every run, so a sink only ever held the last prompt and a regulator
asking what the agent did yesterday got nothing.
"""

import asyncio
import hashlib
import json
from collections import defaultdict
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.audits.file_audit_broker import FileAuditBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.standard_agent import StandardAgent


@pytest.fixture
def audit_path(tmp_path):
    return str(tmp_path / "decision-log.jsonl")


@pytest.fixture
def answering_agent(audit_path):
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = []

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    async def brain(system_prompt, user_prompt):
        return "FINAL: 42"

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .on_brain(brain)
        .audit(audit_path))


def _read_all_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8") as file:
        return file.read().splitlines()


def _run_id_of(line: str) -> str:
    return json.loads(line)["runId"]


def _sequence_of(line: str) -> int:
    return json.loads(line)["sequence"]


def _runs_of(lines: list[str]) -> dict[str, list[str]]:
    runs = defaultdict(list)

    for line in lines:
        runs[_run_id_of(line)].append(line)

    return runs


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_parseable(line: str) -> bool:
    try:
        json.loads(line)

        return True
    except json.JSONDecodeError:
        return False


async def test_should_retain_every_run_in_the_decision_log_on_process_prompt(
        answering_agent,
        audit_path):
    # given
    agent = answering_agent

    # when
    await agent.process_prompt(prompt="the ALPHA question")
    await agent.process_prompt(prompt="the BRAVO question")

    # then: evidence of each prompt is its record's payload hash. The decision log is metadata
    # by default (F-14), so the prompt itself never travels to the sink.
    actual_lines = _read_all_lines(audit_path)

    assert any(_sha256_hex("the ALPHA question") in line for line in actual_lines)
    assert any(_sha256_hex("the BRAVO question") in line for line in actual_lines)
    assert not any("ALPHA" in line for line in actual_lines)

    assert len({_run_id_of(line) for line in actual_lines}) == 2


async def test_should_number_each_run_from_zero_in_the_decision_log_on_process_prompt(
        answering_agent,
        audit_path):
    # given
    agent = answering_agent

    # when
    await agent.process_prompt(prompt="first")
    await agent.process_prompt(prompt="second")

    # then
    actual_lines = _read_all_lines(audit_path)

    for run in _runs_of(actual_lines).values():
        sequences = [_sequence_of(line) for line in run]

        assert sequences == sorted(sequences)
        assert sequences[0] == 0
        assert len(set(sequences)) == len(sequences)


async def test_should_detect_an_altered_or_removed_record_in_the_decision_log(
        answering_agent,
        audit_path):
    # given
    agent = answering_agent

    await agent.process_prompt(prompt="the question")

    written_lines = _read_all_lines(audit_path)

    altered_lines = list(written_lines)
    altered_lines[0] = altered_lines[0].replace("run started", "nothing happened")

    shortened_lines = written_lines[1:]

    # when
    actual_intact_link = FileAuditBroker.find_broken_link(written_lines)
    actual_altered_link = FileAuditBroker.find_broken_link(altered_lines)
    actual_shortened_link = FileAuditBroker.find_broken_link(shortened_lines)

    # then
    assert actual_intact_link is None
    assert actual_altered_link is not None
    assert actual_shortened_link is not None


# SPEC.md 4.4 and 4.7: one instance serves prompts concurrently, records from concurrent runs MAY
# interleave in the sink, and every record MUST still be attributable to exactly one run. This is
# the assertion that caught run identity living in broker instance fields.
async def test_should_keep_concurrent_runs_attributable_in_the_decision_log(
        answering_agent,
        audit_path):
    # given
    agent = answering_agent
    expected_run_count = 64

    # when: one agent instance, sixty-four prompts in flight at once
    await asyncio.gather(*(
        agent.process_prompt(prompt=f"question {index}")
        for index in range(expected_run_count)))

    # then
    actual_lines = _read_all_lines(audit_path)

    assert all(_is_parseable(line) for line in actual_lines)

    runs = _runs_of(actual_lines)

    assert len(runs) == expected_run_count

    for run in runs.values():
        sequences = [_sequence_of(line) for line in run]

        assert len(set(sequences)) == len(sequences)
        assert 0 in sequences


# The regression that opened the enterprise plan: with log_to and audit both on, a single agent
# instance failed seven of eight concurrent prompts with an IOException on the sink. Turning on
# the enterprise features was exactly what made the agent single-threaded.
async def test_should_serve_concurrent_prompts_with_both_sinks_configured(
        answering_agent,
        tmp_path):
    # given
    trace_path = str(tmp_path / "trace.txt")
    agent = answering_agent.log_to(trace_path)
    expected_answer_count = 64

    # when
    actual_answers = await asyncio.gather(*(
        agent.process_prompt(prompt=f"question {index}")
        for index in range(expected_answer_count)))

    # then
    assert len(actual_answers) == expected_answer_count
    assert all(answer == "42" for answer in actual_answers)
