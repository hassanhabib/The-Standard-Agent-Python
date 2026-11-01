# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.skills.exceptions import (
    FailedSkillDependencyException,
    FailedSkillServiceException,
    SkillDependencyException,
    SkillServiceException)
from tests.unit.services.foundations.skills.skill_service_tests import SkillServiceTests


class TestSkillServiceExceptionsRetrieveCatalog(SkillServiceTests):
    def test_should_raise_critical_dependency_exception_on_retrieve_catalog_if_os_error_occurs_and_log_it(
        self) -> None:

        # given
        os_error = OSError(self.create_random_string())

        failed_skill_dependency_exception = FailedSkillDependencyException(
            message="Failed skill dependency error occurred, contact support.",
            inner_exception=os_error)

        expected_exception = SkillDependencyException(
            message="Skill dependency error occurred, contact support.",
            inner_exception=failed_skill_dependency_exception)

        self.skill_broker_mock.select_skills.side_effect = os_error

        # when
        with pytest.raises(SkillDependencyException) as actual_exception:
            asyncio.run(self.skill_service.retrieve_skill_catalog())

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        assert self.skill_broker_mock.mock_calls == [call.select_skills()]
        self.assert_logged_once("log_critical", expected_exception)

    def test_should_raise_service_exception_on_retrieve_catalog_if_service_error_occurs_and_log_it(
        self) -> None:

        # given
        service_error = Exception(self.create_random_string())

        failed_skill_service_exception = FailedSkillServiceException(
            message="Failed skill service error occurred, contact support.",
            inner_exception=service_error)

        expected_exception = SkillServiceException(
            message="Skill service error occurred, contact support.",
            inner_exception=failed_skill_service_exception)

        self.skill_broker_mock.select_skills.side_effect = service_error

        # when
        with pytest.raises(SkillServiceException) as actual_exception:
            asyncio.run(self.skill_service.retrieve_skill_catalog())

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
        assert self.skill_broker_mock.mock_calls == [call.select_skills()]
        self.assert_logged_once("log_error", expected_exception)
