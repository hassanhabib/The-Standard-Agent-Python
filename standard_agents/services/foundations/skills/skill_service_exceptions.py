# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.skills.exceptions import (
    FailedSkillDependencyException,
    SkillDependencyException)


async def try_catch(
    logging_broker: ILoggingBroker,
    returning_string_function: Callable[[], Awaitable[str]]) -> str:

    try:
        return await returning_string_function()
    # Skills the agent cannot read mean the agent cannot be who it was configured to be.
    except OSError as os_error:
        failed_skill_dependency_exception = FailedSkillDependencyException(
            message="Failed skill dependency error occurred, contact support.",
            inner_exception=os_error)

        raise await create_and_log_critical_dependency_exception(
            logging_broker,
            failed_skill_dependency_exception)


async def create_and_log_critical_dependency_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> SkillDependencyException:

    skill_dependency_exception = SkillDependencyException(
        message="Skill dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_critical(skill_dependency_exception)

    return skill_dependency_exception
