# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

from tests.unit.services.foundations.skills.skill_service_tests import SkillServiceTests


class TestSkillServiceLogicRetrieveAll(SkillServiceTests):
    def test_should_retrieve_all_skills_in_name_order(self) -> None:
        # given
        first_skill_name = "10-" + self.create_random_string()
        second_skill_name = "20-" + self.create_random_string()
        first_skill_content = self.create_random_string()
        second_skill_content = self.create_random_string()
        returned_skill_names = [second_skill_name, first_skill_name]

        returned_skill_contents = {
            first_skill_name: first_skill_content,
            second_skill_name: second_skill_content
        }

        expected_skills = first_skill_content + "\n\n" + second_skill_content
        self.skill_broker_mock.select_skill_names.return_value = returned_skill_names

        self.skill_broker_mock.select_skill_content.side_effect = (
            lambda skill_name: returned_skill_contents[skill_name])

        # when
        actual_skills = asyncio.run(self.skill_service.retrieve_all_skills())

        # then
        assert actual_skills == expected_skills

        assert self.skill_broker_mock.mock_calls == [
            call.select_skill_names(),
            call.select_skill_content(first_skill_name),
            call.select_skill_content(second_skill_name)
        ]

        assert self.logging_broker_mock.mock_calls == []
