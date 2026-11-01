# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call


async def test_should_set_system_prompt_from_skill_service_on_recall(
        data_coordination_service,
        skill_service,
        memory_service,
        create_random_agent_context,
        create_random_string):
    # given
    input_context = create_random_agent_context()
    random_skills = create_random_string()
    expected_system_prompt = random_skills
    skill_service.retrieve_skills.return_value = random_skills
    memory_service.recall_memories.return_value = []

    # when
    actual_context = await data_coordination_service.recall(input_context)

    # then
    assert actual_context.system_prompt == expected_system_prompt
    assert skill_service.mock_calls.count(call.retrieve_skills("")) == 1


async def test_should_not_mutate_input_context_on_recall(
        data_coordination_service,
        skill_service,
        memory_service,
        create_random_agent_context,
        create_random_string):
    # given
    input_context = create_random_agent_context()
    original_prompt = input_context.prompt
    random_skills = create_random_string()
    skill_service.retrieve_skills.return_value = random_skills
    memory_service.recall_memories.return_value = []

    # when
    actual_context = await data_coordination_service.recall(input_context)

    # then
    assert input_context.system_prompt == ""
    assert input_context.prompt == original_prompt
    assert actual_context is not input_context
    assert actual_context.prompt == original_prompt
