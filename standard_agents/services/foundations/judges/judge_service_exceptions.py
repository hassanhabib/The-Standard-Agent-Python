# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.foundations.judges.exceptions import (
    FailedJudgeDependencyException,
    InvalidJudgeException,
    JudgeDependencyException,
    JudgeValidationException)
from standard_agents.models.foundations.judges.judgement import Judgement


async def try_catch(
    logging_broker: ILoggingBroker,
    returning_judgement_function: Callable[[], Awaitable[Judgement]]) -> Judgement:

    try:
        return await returning_judgement_function()
    except InvalidJudgeException as invalid_judge_exception:
        raise await create_and_log_validation_exception(
            logging_broker,
            invalid_judge_exception)
    # A Judge is often a model of its own: unreachable (OSError) or failing (RuntimeError).
    except (OSError, RuntimeError) as dependency_error:
        failed_judge_dependency_exception = FailedJudgeDependencyException(
            message="Failed judge dependency error occurred, contact support.",
            inner_exception=dependency_error)

        raise await create_and_log_dependency_exception(
            logging_broker,
            failed_judge_dependency_exception)


async def create_and_log_dependency_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> JudgeDependencyException:

    judge_dependency_exception = JudgeDependencyException(
        message="Judge dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(judge_dependency_exception)

    return judge_dependency_exception


async def create_and_log_validation_exception(
    logging_broker: ILoggingBroker,
    exception: Xeption) -> JudgeValidationException:

    judge_validation_exception = JudgeValidationException(
        message="Judge validation error occurred, fix the errors and try again.",
        inner_exception=exception)

    await logging_broker.log_error(judge_validation_exception)

    return judge_validation_exception
