# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

from standard_agents.models.foundations.skills.skill import Skill


async def test_should_retrieve_skills(
        skill_service, skill_broker, logging_broker, create_random_string):

    # given
    skill_content = create_random_string()
    retrieved_skills = [Skill(name="00-skill.md", content=skill_content)]
    skill_broker.select_skills.return_value = retrieved_skills
    expected_skills = skill_content

    # when
    actual_skills = await skill_service.retrieve_skills()

    # then
    assert actual_skills == expected_skills
    assert skill_broker.mock_calls == [call.select_skills()]
    assert logging_broker.mock_calls == []


async def test_should_return_empty_when_broker_returns_no_skills(
        skill_service, skill_broker, logging_broker):

    # given
    skill_broker.select_skills.return_value = []

    # when
    actual_skills = await skill_service.retrieve_skills()

    # then
    assert actual_skills == ""
    assert skill_broker.mock_calls == [call.select_skills()]
    assert logging_broker.mock_calls == []


async def test_should_compose_skills_in_name_order(
        skill_service, skill_broker, logging_broker, create_random_string):

    # given
    first_skill = create_random_string()
    second_skill = create_random_string()

    unordered_skills = [
        Skill(name="b-second.md", content=second_skill),
        Skill(name="a-first.md", content=first_skill)]

    expected_skills = "\n\n".join((first_skill, second_skill))
    skill_broker.select_skills.return_value = unordered_skills

    # when
    actual_skills = await skill_service.retrieve_skills()

    # then: composed in name order regardless of the order the broker returned
    assert actual_skills == expected_skills
    assert skill_broker.mock_calls == [call.select_skills()]
    assert logging_broker.mock_calls == []


async def test_should_retrieve_only_routed_skill_when_route_is_given(
        skill_service, skill_broker, create_random_string):

    # given
    calculator_skill = create_random_string()
    identity_skill = create_random_string()

    skills = [
        Skill(name="identity-skill.md", content=identity_skill),
        Skill(name="calculator-skill.md", content=calculator_skill)]

    skill_broker.select_skills.return_value = skills

    # when
    actual_skills = await skill_service.retrieve_skills(route="calculator")

    # then: only the skill whose name matches the route label is fanned in
    assert actual_skills == calculator_skill


async def test_should_route_by_nested_folder_name_when_route_is_given(
        skill_service, skill_broker, create_random_string):

    # given: a nested skill is identified by its folder in name
    nested_skill = create_random_string()
    other_skill = create_random_string()

    skills = [
        Skill(name="the-standard-skill/SKILL.md", content=nested_skill),
        Skill(name="other-skill.md", content=other_skill)]

    skill_broker.select_skills.return_value = skills

    # when
    actual_skills = await skill_service.retrieve_skills(route="the-standard-skill")

    # then
    assert actual_skills == nested_skill
