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
