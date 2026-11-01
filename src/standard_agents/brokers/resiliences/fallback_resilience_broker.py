# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, TypeVar

from standard_agents.brokers.resiliences.iresilience_broker import IResilienceBroker
from standard_agents.models.brokers.generators.v1.conversation import GenerationResult

T = TypeVar("T")

# default(DateTimeOffset): the circuit has never opened.
_NEVER = datetime.min.replace(tzinfo=timezone.utc)


# Degradation before failure (SPEC.md 4.10). After enough consecutive failures the primary is
# judged unhealthy and the circuit opens: calls stop going to something that is not answering
# and go to the alternative instead. A degraded answer is worth more than no answer.
#
# It refuses to pretend. With no alternative configured this broker fails rather than returning
# an empty result, because a caller cannot tell fabricated silence from a real one.
#
# The circuit closes again after a cool-down, so a provider that recovers is used again without
# anyone restarting anything.
class FallbackResilienceBroker(IResilienceBroker):
    def __init__(
        self,
        primary: IResilienceBroker,
        alternative: Callable[[], Awaitable[str]] | None = None,
        failures_before_open: int = 3,
        cool_down: timedelta | None = None,
        now: Callable[[], datetime] | None = None) -> None:

        self._primary = primary
        self._alternative = alternative
        self._failures_before_open = failures_before_open
        self._cool_down = timedelta(seconds=30) if cool_down is None else cool_down
        self._now = (lambda: datetime.now(timezone.utc)) if now is None else now

        self._circuit_lock = threading.Lock()
        self._consecutive_failures = 0
        self._opened_on = _NEVER

    @property
    def is_open(self) -> bool:
        with self._circuit_lock:
            return self._is_open_now()

    async def execute(self, operation: Callable[[], Awaitable[T]], result_type: type[T]) -> T:
        if self.is_open:
            return await self._fall_back(result_type)

        try:
            result = await self._primary.execute(operation, result_type)

            with self._circuit_lock:
                self._consecutive_failures = 0

            return result
        except Exception:
            with self._circuit_lock:
                self._consecutive_failures += 1

                now_open = self._consecutive_failures >= self._failures_before_open

                if now_open:
                    self._opened_on = self._now()

            if now_open and self._alternative is not None:
                return await self._fall_back(result_type)

            raise

    def _is_open_now(self) -> bool:
        if self._consecutive_failures < self._failures_before_open:
            return False

        # Cool-down elapsed: close the circuit and let the primary prove itself again.
        if self._now() - self._opened_on >= self._cool_down:
            self._consecutive_failures = 0

            return False

        return True

    async def _fall_back(self, result_type: type[T]) -> T:
        if self._alternative is None:
            raise RuntimeError(
                "The provider is unhealthy and no alternative is configured. Failing rather "
                + "than returning a fabricated result (SPEC.md §4.10).")

        answer = await self._alternative()

        return _degrade(answer, result_type)


# The alternative is text, what a host can write without knowing which protocol will ask for
# it, so each protocol's result is shaped from that text explicitly: the text seam takes it as
# the reply, the native seam takes it as a final answer with no tool calls. A bare cast to T
# held on the first and threw on the second, at the exact moment the control was meant to work
# (principal review 2026-09-04, F-07). A T this broker has not been taught is named rather than
# guessed at.
def _degrade(answer: str, result_type: type[T]) -> T:
    if result_type is str:
        return answer

    if result_type is GenerationResult:
        return GenerationResult(content=answer)

    raise RuntimeError(
        f"No degraded {result_type.__name__} can be shaped from a text fallback. Supply a "
        + "resilience broker that understands this result type (UseResilience).")
