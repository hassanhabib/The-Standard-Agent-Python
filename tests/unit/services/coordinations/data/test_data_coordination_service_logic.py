# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses
from unittest.mock import call

from standard_agents.models.orchestrations.agents.agent_context import AgentContext


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


async def test_should_seed_observations_from_memories_on_recall(
        data_coordination_service,
        skill_service,
        memory_service,
        create_random_agent_context,
        create_random_string):
    # given
    input_context = create_random_agent_context()
    random_skills = create_random_string()
    random_memories = [create_random_string(), create_random_string()]
    skill_service.retrieve_skills.return_value = random_skills
    memory_service.recall_memories.return_value = random_memories

    # when
    actual_context = await data_coordination_service.recall(input_context)

    # then
    assert all(memory in actual_context.observations for memory in random_memories)
    assert memory_service.mock_calls.count(call.recall_memories()) == 1


async def test_should_preserve_existing_observations_on_recall(
        data_coordination_service,
        skill_service,
        memory_service,
        create_random_string):
    # given
    prior_observation = create_random_string()

    input_context = AgentContext(
        prompt=create_random_string(),
        observations=(prior_observation,))

    skill_service.retrieve_skills.return_value = create_random_string()
    memory_service.recall_memories.return_value = []

    # when
    actual_context = await data_coordination_service.recall(input_context)

    # then
    assert prior_observation in actual_context.observations


async def test_should_expand_tools_marker_in_system_prompt_on_recall(
        data_coordination_service,
        skill_service,
        memory_service,
        tool_catalog,
        create_random_agent_context):
    # given
    input_context = create_random_agent_context()
    skills_with_marker = "You may use these tools:\n{{tools}}\nChoose one."
    skill_service.retrieve_skills.return_value = skills_with_marker
    memory_service.recall_memories.return_value = []

    # when
    actual_context = await data_coordination_service.recall(input_context)

    # then
    assert tool_catalog in actual_context.system_prompt
    assert "{{tools}}" not in actual_context.system_prompt


async def test_should_seed_knowledge_into_observations_on_recall(
        data_coordination_service,
        skill_service,
        memory_service,
        knowledge_service,
        create_random_agent_context,
        create_random_knowledge_result,
        create_random_string):
    # given
    input_context = create_random_agent_context()

    random_knowledge_results = [
        create_random_knowledge_result(create_random_string()),
        create_random_knowledge_result("")]

    expected_observations = tuple(
        knowledge_result.text for knowledge_result in random_knowledge_results)

    skill_service.retrieve_skills.return_value = create_random_string()
    memory_service.recall_memories.return_value = []
    knowledge_service.retrieve_sourced_knowledge.return_value = random_knowledge_results

    # when
    actual_context = await data_coordination_service.recall(input_context)

    # then: the passages alone, exactly as an unsourced broker's would read
    assert actual_context.observations == expected_observations

    assert knowledge_service.mock_calls == [
        call.retrieve_sourced_knowledge(input_context.prompt)]


async def test_should_carry_the_sources_of_recalled_knowledge_on_recall(
        data_coordination_service,
        skill_service,
        memory_service,
        knowledge_service,
        create_random_agent_context,
        create_random_knowledge_result,
        create_random_string):
    """The run's sources, once each and in the order first recalled (SPEC.md 3.2).

    Recall runs every turn, so a source an earlier turn recalled is already on the context and
    keeps its place; a passage with no source adds nothing, because it can never be cited.
    """
    # given
    earlier_source = create_random_string()
    new_source = create_random_string()

    input_context = dataclasses.replace(
        create_random_agent_context(),
        grounding_sources=(earlier_source,))

    random_knowledge_results = [
        create_random_knowledge_result(new_source),
        create_random_knowledge_result(""),
        create_random_knowledge_result(earlier_source),
        create_random_knowledge_result(new_source)]

    expected_grounding_sources = (earlier_source, new_source)
    skill_service.retrieve_skills.return_value = create_random_string()
    memory_service.recall_memories.return_value = []
    knowledge_service.retrieve_sourced_knowledge.return_value = random_knowledge_results

    # when
    actual_context = await data_coordination_service.recall(input_context)

    # then
    assert actual_context.grounding_sources == expected_grounding_sources

    assert knowledge_service.mock_calls == [
        call.retrieve_sourced_knowledge(input_context.prompt)]
