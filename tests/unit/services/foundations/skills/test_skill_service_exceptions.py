# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.skills.exceptions import (
    FailedSkillDependencyException,
    FailedSkillServiceException,
    SkillDependencyException,
    SkillServiceException)


def _skill_dependency_exception(inner_exception: Exception) -> SkillDependencyException:
    failed_skill_dependency_exception = FailedSkillDependencyException(
        message="Failed skill dependency error occurred, contact support.",
        inner_exception=inner_exception)

    return SkillDependencyException(
        message="Skill dependency error occurred, contact support.",
        inner_exception=failed_skill_dependency_exception)


@pytest.mark.parametrize(
    "critical_dependency_exception",
    [FileNotFoundError(), NotADirectoryError(), PermissionError()],
    ids=["file-not-found", "directory-not-found", "unauthorized-access"])
async def test_should_throw_dependency_exception_on_retrieve_skills_if_critical_error_occurs_and_log_it(
        critical_dependency_exception,
        skill_service,
        skill_broker,
        logging_broker,
        same_exception_as):

    # given
    expected_skill_dependency_exception = _skill_dependency_exception(
        critical_dependency_exception)

    skill_broker.select_skills.side_effect = critical_dependency_exception

    # when
    with pytest.raises(SkillDependencyException) as raised:
        await skill_service.retrieve_skills()

    # then
    assert raised.value.same_exception_as(expected_skill_dependency_exception)
    assert skill_broker.mock_calls == [call.select_skills()]

    assert logging_broker.mock_calls == [
        call.log_critical(same_exception_as(expected_skill_dependency_exception))]


async def test_should_throw_dependency_exception_on_retrieve_skills_if_io_error_occurs_and_log_it(
        skill_service, skill_broker, logging_broker, same_exception_as):

    # given
    io_error = OSError()
    expected_skill_dependency_exception = _skill_dependency_exception(io_error)
    skill_broker.select_skills.side_effect = io_error

    # when
    with pytest.raises(SkillDependencyException) as raised:
        await skill_service.retrieve_skills()

    # then
    assert raised.value.same_exception_as(expected_skill_dependency_exception)
    assert skill_broker.mock_calls == [call.select_skills()]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_skill_dependency_exception))]


async def test_should_throw_service_exception_on_retrieve_skills_if_service_error_occurs_and_log_it(
        skill_service, skill_broker, logging_broker, same_exception_as):

    # given
    service_error = Exception()

    failed_skill_service_exception = FailedSkillServiceException(
        message="Failed skill service error occurred, contact support.",
        inner_exception=service_error)

    expected_skill_service_exception = SkillServiceException(
        message="Skill service error occurred, contact support.",
        inner_exception=failed_skill_service_exception)

    skill_broker.select_skills.side_effect = service_error

    # when
    with pytest.raises(SkillServiceException) as raised:
        await skill_service.retrieve_skills()

    # then
    assert raised.value.same_exception_as(expected_skill_service_exception)
    assert skill_broker.mock_calls == [call.select_skills()]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_skill_service_exception))]
