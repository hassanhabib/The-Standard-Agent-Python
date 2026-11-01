# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The human-readable trace at each verbosity: turns always, steps and processes as asked."""

from unittest.mock import create_autospec

from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.loggings.trace_verbosity import TraceVerbosity
from standard_agents.standard_agent import StandardAgent


async def _to_stream(*tokens: str):
    for token in tokens:
        yield token


def _create_tracing_agent(log_path: str, verbosity: TraceVerbosity) -> StandardAgent:
    generator_broker = create_autospec(GeneratorBroker, instance=True)

    # A loose Moq mock answers an unarranged bool with false: the broker does not put request
    # options on the wire.
    generator_broker.honors_request = False

    generator_broker.generate_stream.side_effect = (
        lambda system_prompt, user_prompt, inference=None: _to_stream("FINAL: 42"))

    generator_broker.generate.return_value = "FINAL: 42"

    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = [Skill(content="Answer directly.")]

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    classifier_broker = create_autospec(ClassifierBroker, instance=True)
    classifier_broker.classify.return_value = "allow"

    # A loose Moq mock answers an unarranged string with null.
    classifier_broker.assess.return_value = None

    verifier_broker = create_autospec(VerifierBroker, instance=True)
    verifier_broker.verify.return_value = "1.0"

    mcp_broker = create_autospec(McpBroker, instance=True)

    # A loose Moq mock answers an unarranged list with an empty one: the server has no tools.
    mcp_broker.list_tools.return_value = []

    return (StandardAgent()
        .use_generator(generator_broker)
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .use_gate(classifier_broker)
        .use_judge(verifier_broker)
        .use_mcp(mcp_broker)
        .log_to(log_path, verbosity=verbosity))


async def _run_and_read_transcript(tmp_path, verbosity: TraceVerbosity) -> str:
    log_path = str(tmp_path / "trace.txt")
    agent = _create_tracing_agent(log_path, verbosity)

    async for _ in agent.process_prompt_stream("what is the answer?"):
        pass

    with open(log_path, encoding="utf-8") as file:
        return file.read()


async def test_should_write_turn_step_process_transcript_at_full_verbosity(tmp_path):
    # given . when
    transcript = await _run_and_read_transcript(tmp_path, TraceVerbosity.FULL)

    # then
    assert "Turn 0" in transcript
    assert "Step 0: Data" in transcript
    assert "Process 0: Data: Received prompt" in transcript
    assert "Step 1: Decision" in transcript
    assert "Gate" in transcript
    assert "Judge" in transcript
    assert "Step 2: Direction" in transcript


async def test_should_omit_steps_and_processes_at_summary_verbosity(tmp_path):
    # given . when
    transcript = await _run_and_read_transcript(tmp_path, TraceVerbosity.SUMMARY)

    # then
    assert "Turn 0" in transcript
    assert "Step 0: Data" not in transcript
    assert "Process 0:" not in transcript


async def test_should_show_natures_but_not_detail_processes_at_natures_verbosity(tmp_path):
    # given . when
    transcript = await _run_and_read_transcript(tmp_path, TraceVerbosity.NATURES)

    # then
    assert "Step 1: Decision" in transcript
    assert "Gate" in transcript
    assert "Retrieved skills" not in transcript
