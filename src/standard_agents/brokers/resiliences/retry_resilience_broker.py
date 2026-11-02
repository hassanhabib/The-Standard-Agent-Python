# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import random
from datetime import timedelta
from collections.abc import Awaitable, Callable
from typing import TypeVar

from restfulsense.exceptions import HttpRequestException
from standard_agents.brokers.resiliences.resilience_broker import ResilienceBroker
from xeptions import Xeption

T = TypeVar("T")


class RetryResilienceBroker(ResilienceBroker):
    """Retry with exponential backoff and jitter (SPEC.md 4.10).

    What is retryable is decided by the error's CATEGORY, never its text. The framework already
    localizes every failure into a Xeption category, so that classification is available for
    free and does not have to be re-derived from a message that a provider may reword at any
    time.

    The rule is narrow on purpose: a dependency failure is the network having a bad moment, so
    it is worth another attempt. A validation failure is the request being wrong, so retrying it
    will fail identically and only spends the budget.
    """

    def __init__(
            self,
            retries: int = 3,
            initial_delay: timedelta | None = None,
            delay: Callable[[timedelta], Awaitable[None]] | None = None) -> None:

        self._max_attempts = 1 if retries < 0 else retries + 1

        self._initial_delay = (
            timedelta(milliseconds=200) if initial_delay is None else initial_delay)

        self._delay = _wait if delay is None else delay

    async def execute(self, operation: Callable[[], Awaitable[T]], result_type: type[T]) -> T:
        attempt = 1

        while True:
            try:
                return await operation()
            except Exception as exception:
                if not (attempt < self._max_attempts and _is_transient(exception)):
                    raise

                await self._delay(self._backoff_for(attempt))

            attempt += 1

    def _backoff_for(self, attempt: int) -> timedelta:
        """The exponential delay before the next attempt, plus up to half again of jitter.

        Jitter matters when many agents share one provider: without it every agent that failed
        at the same instant retries at the same instant, and the recovering provider is hit by
        the same spike that knocked it over.
        """
        exponential = (self._initial_delay / timedelta(milliseconds=1)) * 2.0 ** (attempt - 1)
        jitter = random.random() * exponential * 0.5

        return timedelta(milliseconds=exponential + jitter)


async def _wait(wait: timedelta) -> None:
    await asyncio.sleep(wait.total_seconds())


def _is_transient(exception: Exception) -> bool:
    """Whether a failure may not happen again, judged by the framework's own categories.

    A dependency failed, which may not fail again. A *DependencyValidation* failure is the
    request being wrong and is never retried. A cancelled call is never retried either; in
    Python it is not an Exception and never reaches here.
    """
    if isinstance(exception, Xeption) and _is_dependency_failure(exception):
        return True

    if isinstance(exception, HttpRequestException):
        return _is_transient_status(exception.status_code)

    return False


def _is_dependency_failure(exception: Exception) -> bool:
    name = type(exception).__name__

    return (
        name.endswith("DependencyException")
        and not name.endswith("DependencyValidationException"))


def _is_transient_status(status: int | None) -> bool:
    """Whether a status is worth another attempt.

    No status (the request never got an answer), a request timeout, too many requests, or any
    server failure.
    """
    return status is None or status in (408, 429) or status >= 500
