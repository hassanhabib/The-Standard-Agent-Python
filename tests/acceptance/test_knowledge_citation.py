# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""SPEC.md 4.2: a grounded answer cites its sources.

The agent cites, not the model. Asking a model to name its sources produces a citation when the
model feels like writing one, which is not a citation anyone can rely on: a bank's policy bot, a
helpdesk answering from runbooks and a coding agent answering from API references all need the
line to be a fact the run knows. These pin the rules that make it one: opt-in, after the Judge,
the same on every door, and never on a run that did not answer.
"""

from unittest.mock import create_autospec

from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent

_REFUNDS_SOURCE = "Refund Policy (2026)"
_SHIPPING_SOURCE = "Shipping Handbook"
_ANSWER = "Enterprise customers may request a refund within 90 days."


def _grounding_results() -> list[KnowledgeResult]:
    return [
        KnowledgeResult(
            text="Refund policy. Enterprise customers may request a refund within 90 days.",
            score=0.91,
            source=_REFUNDS_SOURCE),
        KnowledgeResult(
            text="Refunds go back to the original payment method.",
            score=0.42,
            source=_SHIPPING_SOURCE)]


def _empty_skill_broker() -> SkillBroker:
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = []

    return skill_broker


def _empty_memory_broker() -> MemoryBroker:
    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    return memory_broker


def _grounded_agent(brain) -> StandardAgent:
    knowledge_results = _grounding_results()

    async def retrieve(query):
        return knowledge_results

    return (StandardAgent()
        .use_skills(_empty_skill_broker())
        .use_memory(_empty_memory_broker())
        .on_sourced_knowledge(retrieve)
        .on_brain(brain))


def _answering(answer: str):
    async def brain(system_prompt, user_prompt):
        return f"FINAL: {answer}"

    return brain


async def test_should_cite_the_sources_that_grounded_an_answer():
    # given
    agent = _grounded_agent(_answering(_ANSWER)).cite_knowledge()
    expected_result = f"{_ANSWER}\n\nSource: {_REFUNDS_SOURCE}\nSource: {_SHIPPING_SOURCE}"

    # when
    actual_result = await agent.process_prompt("what is the refund window?")

    # then
    assert actual_result == expected_result


async def test_should_return_the_answer_unchanged_when_citation_was_never_asked_for():
    # given
    agent = _grounded_agent(_answering(_ANSWER))

    # when
    actual_result = await agent.process_prompt("what is the refund window?")

    # then: byte for byte the answer an agent without citation always returned
    assert actual_result == _ANSWER


# The passage reaches the brain exactly as an unsourced broker's would (SPEC.md 3.7): the source
# rides the run, not the observation, so the model is shown what it was always shown.
async def test_should_show_the_brain_the_passage_without_its_source():
    # given
    seen_by_brain = ""

    async def brain(system_prompt, user_prompt):
        nonlocal seen_by_brain
        seen_by_brain = user_prompt

        return f"FINAL: {_ANSWER}"

    agent = _grounded_agent(brain).cite_knowledge()

    # when
    await agent.process_prompt("what is the refund window?")

    # then
    assert "within 90 days" in seen_by_brain
    assert _REFUNDS_SOURCE not in seen_by_brain


async def test_should_not_repeat_a_source_the_answer_already_credits():
    # given
    credited_answer = f"{_ANSWER}\n\nsource: {_REFUNDS_SOURCE}"
    agent = _grounded_agent(_answering(credited_answer)).cite_knowledge()
    expected_result = f"{credited_answer}\n\nSource: {_SHIPPING_SOURCE}"

    # when
    actual_result = await agent.process_prompt("what is the refund window?")

    # then
    assert actual_result == expected_result


async def test_should_cite_with_the_configured_prefix():
    # given
    agent = _grounded_agent(_answering(_ANSWER)).cite_knowledge(prefix="Reference: ")

    expected_result = (
        f"{_ANSWER}\n\nReference: {_REFUNDS_SOURCE}\nReference: {_SHIPPING_SOURCE}")

    # when
    actual_result = await agent.process_prompt("what is the refund window?")

    # then
    assert actual_result == expected_result


# A passage whose origin is unknown is never cited (SPEC.md 3.7), which is every passage a plain
# broker returns, so an agent that turns citation on over a plain broker answers as it always did
# rather than crediting a blank.
async def test_should_not_cite_knowledge_whose_source_is_unknown():
    # given
    passages = ["Refund policy. Enterprise customers may request a refund within 90 days."]

    async def retrieve(query):
        return passages

    agent = (StandardAgent()
        .use_skills(_empty_skill_broker())
        .use_memory(_empty_memory_broker())
        .on_knowledge(retrieve)
        .on_brain(_answering(_ANSWER))
        .cite_knowledge())

    # when
    actual_result = await agent.process_prompt("what is the refund window?")

    # then
    assert actual_result == _ANSWER


async def test_should_not_cite_a_run_that_did_not_answer():
    # given: the knowledge is recalled, then the Gate refuses the task
    async def gate(gate_prompt, input):
        return "refuse: out of scope"

    agent = (_grounded_agent(_answering(_ANSWER))
        .on_gate(gate)
        .cite_knowledge())

    # when
    actual_outcome = await agent.run("what is the refund window?")

    # then
    assert actual_outcome.status == AgentStatus.REFUSED
    assert "Source:" not in actual_outcome.result


# An answer held to a response schema is a document the caller will parse; a line appended after
# it breaks the very shape the caller was promised (SPEC.md 4.2).
async def test_should_not_cite_an_answer_held_to_a_response_schema():
    # given
    json_answer = '{"refundDays":90}'
    agent = _grounded_agent(_answering(json_answer)).cite_knowledge()

    request = PromptRequest(
        prompt="what is the refund window?",
        response_schema_json='{"type":"object"}')

    # when
    actual_result = await agent.process_prompt(request)

    # then
    assert actual_result == json_answer


# The Judge scores the model's answer; lines the agent wrote are not the model's work, and a Judge
# shown them is scoring the agent (SPEC.md 4.2).
async def test_should_cite_after_the_judge():
    # given
    seen_by_judge = []

    async def judge(judge_prompt, candidate):
        seen_by_judge.append(candidate)

        return "1.0"

    agent = (_grounded_agent(_answering(_ANSWER))
        .on_judge(judge)
        .cite_knowledge())

    # when
    actual_result = await agent.process_prompt("what is the refund window?")

    # then
    assert seen_by_judge
    assert all("Source:" not in candidate for candidate in seen_by_judge)
    assert actual_result.endswith(f"Source: {_SHIPPING_SOURCE}")


async def test_should_cite_when_the_request_asks_and_the_agent_expressed_no_opinion():
    # given
    agent = _grounded_agent(_answering(_ANSWER))
    request = PromptRequest(prompt="what is the refund window?", cite_knowledge=True)

    # when
    actual_result = await agent.process_prompt(request)

    # then
    assert actual_result.endswith(f"Source: {_REFUNDS_SOURCE}\nSource: {_SHIPPING_SOURCE}")


# A deployment that must cite, a regulated answer, cannot be switched off by a caller.
async def test_should_keep_citing_when_the_deployment_requires_it_and_the_request_declines():
    # given
    agent = _grounded_agent(_answering(_ANSWER)).cite_knowledge()
    request = PromptRequest(prompt="what is the refund window?", cite_knowledge=False)

    # when
    actual_result = await agent.process_prompt(request)

    # then
    assert actual_result.endswith(f"Source: {_REFUNDS_SOURCE}\nSource: {_SHIPPING_SOURCE}")


# A deployment that never cites cannot be switched on by a caller either.
async def test_should_not_cite_when_the_deployment_forbids_it_and_the_request_asks():
    # given
    agent = _grounded_agent(_answering(_ANSWER)).cite_knowledge(cite=False)
    request = PromptRequest(prompt="what is the refund window?", cite_knowledge=True)

    # when
    actual_result = await agent.process_prompt(request)

    # then
    assert actual_result == _ANSWER


# One answer on every door (SPEC.md 4.2, 4.14): the streamed response and the streamed outcome
# carry the same cited text the batched door returns.
async def test_should_cite_the_same_answer_on_the_streamed_door():
    # given
    agent = _grounded_agent(_answering(_ANSWER)).cite_knowledge()
    expected_result = await agent.process_prompt("what is the refund window?")
    request = PromptRequest(prompt="what is the refund window?")

    # when
    run_stream = agent.run_stream(request)
    streamed_events = [streamed_event async for streamed_event in run_stream]

    # then
    assert expected_result.endswith(f"Source: {_SHIPPING_SOURCE}")

    assert any(
        streamed_event.type == AgentStreamEventType.RESPONSE
        and streamed_event.content == expected_result
        for streamed_event in streamed_events)

    assert run_stream.outcome.result == expected_result


# The session records the answer the caller was given (SPEC.md 4.11), so the next prompt in the
# conversation is told what the agent actually said.
async def test_should_record_the_cited_answer_in_the_session(tmp_path):
    # given
    seen_by_brain = ""

    async def brain(system_prompt, user_prompt):
        nonlocal seen_by_brain
        seen_by_brain = user_prompt

        return f"FINAL: {_ANSWER}"

    agent = (_grounded_agent(brain)
        .sessions(str(tmp_path))
        .cite_knowledge())

    # when
    await agent.process_prompt("what is the refund window?", session_id="customer-1")
    await agent.process_prompt("and for small businesses?", session_id="customer-1")

    # then
    assert f"Source: {_REFUNDS_SOURCE}" in seen_by_brain
