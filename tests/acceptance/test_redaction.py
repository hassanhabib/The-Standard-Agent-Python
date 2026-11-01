# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""SPEC.md 4.6, end to end through the real composition.

These used to be four unit tests, one per service, back when each of Brain, Gate and Judge held
its own redaction broker. Redaction is now a decoration applied at composition, so the failure
worth guarding against changed: not "a service forgot to redact" but "a broker was left
unwrapped". Only a test that drives the whole composition can see that, which is why these
moved up rather than moving sideways onto the decorators.
"""

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.models.brokers.generators.v1.conversation import (
    GenerationResult,
    ModelToolCall)
from standard_agents.models.foundations.brains.redaction_rule import RedactionRule
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool

_SECRET_EMAIL = "jane@acme.com"


async def _select_no_skills():
    return []


async def _recall_nothing():
    return []


async def _remember_nothing(memory):
    return None


async def _retrieve_nothing(query):
    return []


def _agent_that_redacts(brain, gate=None, judge=None) -> StandardAgent:
    agent = (StandardAgent()
        .on_skills(_select_no_skills)
        .on_memory(_recall_nothing, _remember_nothing)
        .on_knowledge(_retrieve_nothing)
        .on_brain(brain)
        .redact())

    if gate is not None:
        agent = agent.on_gate(gate)

    if judge is not None:
        agent = agent.on_judge(judge)

    return agent


async def test_should_hide_the_value_from_the_brain_and_give_it_back_to_the_caller():
    # given
    seen_by_brain = ""

    async def brain(system_prompt, user_prompt):
        nonlocal seen_by_brain
        seen_by_brain = user_prompt

        return "FINAL: I emailed {{EMAIL_0}} as requested."

    agent = _agent_that_redacts(brain)

    # when
    actual_answer = await agent.process_prompt(f"please email {_SECRET_EMAIL} the report")

    # then
    assert _SECRET_EMAIL not in seen_by_brain
    assert "{{EMAIL_0}}" in seen_by_brain
    assert actual_answer == f"I emailed {_SECRET_EMAIL} as requested."


async def test_should_hide_the_value_from_the_gate():
    """The Gate screens the raw task, so it sees exactly what redaction exists to hide, and a
    guardian may run on a different host than the Brain, which makes an unredacted Gate a wider
    exposure than an unredacted Brain, not a narrower one."""
    # given
    seen_by_gate = ""

    async def brain(system_prompt, user_prompt):
        return "FINAL: done"

    async def gate(rubric, input):
        nonlocal seen_by_gate
        seen_by_gate = input

        return "accept"

    agent = _agent_that_redacts(brain=brain, gate=gate)

    # when
    await agent.process_prompt(f"please email {_SECRET_EMAIL} the report")

    # then
    assert seen_by_gate != ""
    assert _SECRET_EMAIL not in seen_by_gate


async def test_should_hide_the_value_from_the_judge():
    """The Judge reads the task AND the drafted answer, so it sees more sensitive text than any
    other guardian, and it is the one most likely to be pointed at a cheap third-party endpoint,
    because scoring is the cheapest of the three calls."""
    # given
    seen_by_judge = ""

    async def brain(system_prompt, user_prompt):
        return f"FINAL: sent to {_SECRET_EMAIL}"

    async def judge(rubric, input):
        nonlocal seen_by_judge
        seen_by_judge = input

        return "1.0"

    agent = _agent_that_redacts(brain=brain, judge=judge)

    # when
    await agent.process_prompt(f"please email {_SECRET_EMAIL} the report")

    # then
    assert seen_by_judge != ""
    assert _SECRET_EMAIL not in seen_by_judge


class _SplittingGeneratorBroker(GeneratorBroker):
    """A placeholder can arrive split across two chunks. Without the streaming buffer the caller
    sees "{{EMAIL_" and never gets the value back."""

    def __init__(self) -> None:
        self.seen_user_prompt = ""

    async def generate(self, system_prompt, user_prompt, *, inference=None):
        self.seen_user_prompt = user_prompt

        return "FINAL: done"

    async def generate_stream(self, system_prompt, user_prompt, *, inference=None):
        self.seen_user_prompt = user_prompt

        yield "FINAL: sent to {{EMAI"
        yield "L_0}} just now"


async def test_should_rehydrate_a_streamed_value_split_across_chunks():
    # given
    generator = _SplittingGeneratorBroker()

    agent = (StandardAgent()
        .on_skills(_select_no_skills)
        .on_memory(_recall_nothing, _remember_nothing)
        .on_knowledge(_retrieve_nothing)
        .use_generator(generator)
        .redact())

    # when
    streamed = []

    async for stream_event in agent.process_prompt_stream(
            f"please email {_SECRET_EMAIL} the report"):
        streamed.append(stream_event.content)

    # then
    assert _SECRET_EMAIL not in generator.seen_user_prompt

    whole = "".join(streamed)

    assert _SECRET_EMAIL in whole
    assert "{{EMAI" not in whole


async def test_should_not_redact_when_redaction_is_not_configured():
    # given: redaction is opt-in; absent it the agent behaves as if 4.6 did not exist
    seen_by_brain = ""

    async def brain(system_prompt, user_prompt):
        nonlocal seen_by_brain
        seen_by_brain = user_prompt

        return "FINAL: done"

    agent = (StandardAgent()
        .on_skills(_select_no_skills)
        .on_memory(_recall_nothing, _remember_nothing)
        .on_knowledge(_retrieve_nothing)
        .on_brain(brain))

    # when
    await agent.process_prompt(f"please email {_SECRET_EMAIL} the report")

    # then
    assert _SECRET_EMAIL in seen_by_brain
