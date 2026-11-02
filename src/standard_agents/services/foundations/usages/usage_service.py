# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from restfulsense import HttpRequestException
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.usages.usage_broker import UsageBroker
from standard_agents.models.foundations.usages.agent_usage import AgentUsage
from standard_agents.models.foundations.usages.exceptions import (
    FailedUsageDependencyException,
    FailedUsageServiceException,
    InvalidUsageException,
    UsageDependencyException,
    UsageServiceException,
    UsageValidationException)
from xeptions import Xeption


class UsageService:
    """What a model call consumed, the question Decision could not answer.

    Inference could say what the model SAID and not what it COST. On the native protocol the
    provider reports usage in its response and the numbers were lifted out as they went past; on
    the text protocol there was nobody to ask, so the token counts stayed zero and a token or cost
    budget never tripped at all. A budget that silently does not apply is worse than no budget,
    because it is claimed in the profile.

    Measuring belongs to Decision because a token is the model's unit. Deciding whether to
    CONTINUE belongs to the loop, which is where the budget already lives.
    """

    def __init__(self, *, usage_broker: UsageBroker, logging_broker: LoggingBroker) -> None:
        self.usage_broker = usage_broker
        self.logging_broker = logging_broker

    async def measure(self, prompt: str, completion: str) -> AgentUsage:
        """What one model call consumed, counted locally.

        Returned with is_estimated set, because a counted number is an estimate of what the
        provider will bill.
        """
        async with _handling_exceptions(self.logging_broker):
            _validate_text(prompt, "prompt")
            _validate_text(completion, "completion")

            prompt_tokens = await self.usage_broker.count_tokens(prompt)
            completion_tokens = await self.usage_broker.count_tokens(completion)

            _validate_count(prompt_tokens)
            _validate_count(completion_tokens)

            return AgentUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                is_estimated=True)


def _validate_text(text: str | None, name: str) -> None:
    """Rejects missing text; empty text is a legitimate measurement.

    A call with no completion consumed no completion tokens. None is not: it is a caller that lost
    the text it meant to charge for, and measuring it as zero would quietly under-bill the run.
    """
    if text is None:
        raise InvalidUsageException(
            message=f"Invalid usage, {name} is required. Please correct the error and try again.")


def _validate_count(tokens: int) -> None:
    """Rejects a negative count, which would subtract from the run's spend.

    That turns a budget into a thing an unusual reply can extend. A custom counter is host code,
    so this is reachable.
    """
    if tokens < 0:
        raise InvalidUsageException(
            message="Invalid usage, token count cannot be negative. "
                "Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidUsageException as invalid_usage_exception:
        raise await _create_and_log_validation_exception(logging_broker, invalid_usage_exception)

    # A counter that cannot be reached is a dependency failure, not a service one: the caller can
    # carry on with a reported number, and only knows to if the failure names the counter rather
    # than the measurement. TimeoutError stands for .NET's TaskCanceledException, which is how
    # HttpClient reports a timeout; asyncio.CancelledError is left to propagate.
    except (HttpRequestException, TimeoutError) as dependency_error:
        failed_usage_dependency_exception = FailedUsageDependencyException(
            message="Failed usage dependency error occurred, contact support.",
            inner_exception=dependency_error)

        raise await _create_and_log_dependency_exception(
            logging_broker, failed_usage_dependency_exception)
    except Exception as exception:
        failed_usage_service_exception = FailedUsageServiceException(
            message="Failed usage service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_usage_service_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> UsageValidationException:

    usage_validation_exception = UsageValidationException(
        message="Usage validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(usage_validation_exception)

    return usage_validation_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> UsageDependencyException:

    usage_dependency_exception = UsageDependencyException(
        message="Usage dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(usage_dependency_exception)

    return usage_dependency_exception


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> UsageServiceException:

    usage_service_exception = UsageServiceException(
        message="Usage service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(usage_service_exception)

    return usage_service_exception
