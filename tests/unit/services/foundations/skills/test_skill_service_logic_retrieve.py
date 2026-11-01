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

    # SPEC.md 4.2: a skill MAY carry its name and description as metadata, which is stripped
    # from the body the brain reads, and the declared name is the one skills are ordered by.
    def test_should_retrieve_skills_without_their_frontmatter(self) -> None:
        # given
        random_body = self.create_random_string() + "\n" + self.create_random_string()

        described_skill = Skill(
            name="z-" + self.create_random_string(),
            content=(
                "---\n"
                + "name: a-first\n"
                + f"description: {self.create_random_string()}\n"
                + "---\n"
                + random_body))

        plain_skill = Skill(name="m-" + self.create_random_string(), content="plain")
        expected_skills = random_body + "\n\n" + plain_skill.content
        self.skill_broker_mock.select_skills.return_value = [plain_skill, described_skill]

        # when
        actual_skills = asyncio.run(self.skill_service.retrieve_skills())

        # then
        assert actual_skills == expected_skills
