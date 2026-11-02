# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The telemetry seam's three access modes (SPEC.md 4.8): Local is .telemetry() and emits through
# an activity source, which only a listener can observe; the broker it composes is covered at the
# broker seam instead. External and Custom are observed directly, which also proves composition
# hands the broker to the loop at all.

from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.telemetries.telemetry_broker import TelemetryBroker
from standard_agents.standard_agent import StandardAgent


@pytest.fixture
def answering_agent(create_skill_broker, empty_memory_broker, empty_knowledge_broker):
    async def brain(system_prompt, user_prompt):
        return "FINAL: 42"

    return (StandardAgent()
        .use_skills(create_skill_broker())
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_brain(brain))


async def test_should_emit_to_external_telemetry_broker_on_process_prompt(answering_agent):
    # given
    telemetry_broker = create_autospec(TelemetryBroker, instance=True)

    # A loose Moq mock answers an unarranged IDisposable with null: no scope to close.
    telemetry_broker.start_run.return_value = None
    telemetry_broker.start_turn.return_value = None

    agent = answering_agent.use_telemetry(telemetry_broker)

    # when
    await agent.process_prompt(prompt="what is the answer?")

    # then
    assert telemetry_broker.start_run.call_count == 1
    assert telemetry_broker.record_run_outcome.call_count == 1


async def test_should_emit_to_custom_telemetry_delegate_on_process_prompt(answering_agent):
    # given
    captured_events = []

    agent = answering_agent.on_telemetry(
        lambda event_name, attributes: captured_events.append(event_name))

    # when
    await agent.process_prompt(prompt="what is the answer?")

    # then
    assert "run.start" in captured_events
    assert "turn.start" in captured_events
    assert "turn.usage" in captured_events
    assert "run.outcome" in captured_events
    assert "run.end" in captured_events
