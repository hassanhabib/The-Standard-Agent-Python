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
