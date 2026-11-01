# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from standard_agents.brokers.resiliences.resilience_broker import ResilienceBroker

T = TypeVar("T")


class NotConfiguredResilienceBroker(ResilienceBroker):
    """The default: run it once, let it fail.

    Absent configuration the agent behaves exactly as it did before retries existed.
    """

    async def execute(self, operation: Callable[[], Awaitable[T]], result_type: type[T]) -> T:
        return await operation()
