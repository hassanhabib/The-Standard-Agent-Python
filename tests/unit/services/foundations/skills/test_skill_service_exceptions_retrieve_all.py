# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.skills.exceptions import (
    FailedSkillDependencyException,
    SkillDependencyException)
from tests.unit.services.foundations.skills.skill_service_tests import SkillServiceTests


class TestSkillServiceExceptionsRetrieveAll(SkillServiceTests):
    def test_should_raise_critical_dependency_exception_on_retrieve_all_if_os_error_occurs_and_log_it(
        self) -> None:

        # given
        os_error = OSError(self.create_random_string())

        failed_skill_dependency_exception = FailedSkillDependencyException(
            message="Failed skill dependency error occurred, contact support.",
            inner_exception=os_error)

        expected_skill_dependency_exception = SkillDependencyException(
            message="Skill dependency error occurred, contact support.",
            inner_exception=failed_skill_dependency_exception)

        self.skill_broker_mock.select_skill_names.side_effect = os_error

        # when
        with pytest.raises(SkillDependencyException) as actual_skill_dependency_exception:
            asyncio.run(self.skill_service.retrieve_all_skills())

        # then
        assert expected_skill_dependency_exception.same_exception_as(
            actual_skill_dependency_exception.value)

        assert self.skill_broker_mock.mock_calls == [call.select_skill_names()]
        self.assert_logged_once("log_critical", expected_skill_dependency_exception)
