# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable, TypeVar

from standard_agents.brokers.resiliences.iresilience_broker import IResilienceBroker

T = TypeVar("T")


# The default: run it once, let it fail. Absent configuration the agent behaves exactly as it
# did before retries existed.
class NotConfiguredResilienceBroker(IResilienceBroker):
    async def execute(self, operation: Callable[[], Awaitable[T]], result_type: type[T]) -> T:
        return await operation()
