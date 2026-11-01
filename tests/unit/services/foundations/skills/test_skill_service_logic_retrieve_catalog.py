# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

from standard_agents.models.foundations.skills.skill import Skill
from tests.unit.services.foundations.skills.skill_service_tests import SkillServiceTests


class TestSkillServiceLogicRetrieveCatalog(SkillServiceTests):
    # SPEC.md 4.2: the catalog is the index of described skills, name and description, in name
    # order. A description is the opt-in: a skill without one is never advertised.
    def test_should_retrieve_the_catalog_of_described_skills(self) -> None:
        # given
        random_description = self.create_random_string()

        frontmatter_skill = Skill(
            name="z.md",
            content=f"---\nname: a-refunds\ndescription: {random_description}\n---\nbody")

        described_skill = Skill(
            name="m-greetings",
            content=self.create_random_string(),
            description="greets people")

        undescribed_skill = Skill(name="b-plain", content=self.create_random_string())

        expected_catalog = (
            f"- a-refunds: {random_description}\n"
            + "- m-greetings: greets people")

        self.skill_broker_mock.select_skills.return_value = [
            undescribed_skill,
            described_skill,
            frontmatter_skill
        ]

        # when
        actual_catalog = asyncio.run(self.skill_service.retrieve_skill_catalog())

        # then
        assert actual_catalog == expected_catalog
        assert self.skill_broker_mock.mock_calls == [call.select_skills()]
        assert self.logging_broker_mock.mock_calls == []
