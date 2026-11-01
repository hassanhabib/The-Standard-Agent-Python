# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses
from unittest.mock import ANY, call

ARABIC_OR_ENGLISH = "CONFLICT: Arabic | answer in Arabic || English | answer in English"


async def test_should_await_input_on_think_if_skills_conflict(
        decision_coordination_service,
        gate_service,
        brain_service,
        create_random_agent_context,
        create_random_string,
        setup_gate_allows,
        setup_judge_approves):

    # given
    input_context = dataclasses.replace(
        create_random_agent_context(),
        system_prompt=create_random_string())

    setup_gate_allows()
    setup_judge_approves()

    gate_service.detect_conflict.side_effect = lambda instructions: (
        ARABIC_OR_ENGLISH if instructions == input_context.system_prompt else None)

    brain_service.generate.return_value = "FINAL: whatever"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "AwaitInput"
    assert "Arabic" in actual_context.payload
    assert "English" in actual_context.payload
    assert brain_service.generate.mock_calls == []


async def test_should_auto_resolve_skill_conflict_from_learned_preference_on_think(
        decision_coordination_service,
        gate_service,
        brain_service,
        create_random_agent_context,
        create_random_string,
        setup_gate_allows,
        setup_judge_approves):

    # given
    input_context = dataclasses.replace(
        create_random_agent_context(),
        system_prompt=create_random_string(),
        observations=("SKILL_PREFERENCE::arabic|english::Arabic",))

    setup_gate_allows()
    setup_judge_approves()
    gate_service.detect_conflict.return_value = ARABIC_OR_ENGLISH
    brain_service.generate.return_value = "FINAL: an answer"

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "ReturnResponse"
    assert brain_service.generate.mock_calls == [call(system_prompt=ANY, user_prompt=ANY)]


async def test_should_learn_preference_on_think_if_prompt_answers_skill_conflict(
        decision_coordination_service,
        gate_service,
        brain_service,
        create_random_agent_context,
        create_random_string,
        setup_gate_allows):

    # given
    input_context = dataclasses.replace(
        create_random_agent_context(),
        prompt="Arabic",
        system_prompt=create_random_string())

    setup_gate_allows()
    gate_service.detect_conflict.return_value = ARABIC_OR_ENGLISH

    # when
    actual_context = await decision_coordination_service.think(input_context)

    # then
    assert actual_context.direction_type == "ReturnResponse"
    assert "Arabic" in actual_context.payload
    assert actual_context.remember.startswith("SKILL_PREFERENCE::")
    assert actual_context.remember.endswith("Arabic")
    assert brain_service.generate.mock_calls == []
