# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

from standard_agents.models.foundations.skills.skill import Skill
from tests.unit.services.foundations.skills.skill_service_tests import SkillServiceTests


class TestSkillServiceLogicRetrieve(SkillServiceTests):
    # Skills compose into the system prompt in name order, so a deployment decides precedence by
    # naming its files (00-assistant.md before 10-calculator.md).
    def test_should_retrieve_skills_in_name_order(self) -> None:
        # given
        first_skill = Skill(
            name="10-" + self.create_random_string(),
            content=self.create_random_string())

        second_skill = Skill(
            name="20-" + self.create_random_string(),
            content=self.create_random_string())

        returned_skills = [second_skill, first_skill]
        expected_skills = first_skill.content + "\n\n" + second_skill.content
        self.skill_broker_mock.select_skills.return_value = returned_skills

        # when
        actual_skills = asyncio.run(self.skill_service.retrieve_skills())

        # then
        assert actual_skills == expected_skills
        assert self.skill_broker_mock.mock_calls == [call.select_skills()]
        assert self.logging_broker_mock.mock_calls == []
