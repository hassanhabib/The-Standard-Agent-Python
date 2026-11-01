# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable

from standard_agents.brokers.usages.iusage_broker import IUsageBroker


# The Custom mode's substrate: a host-supplied counter, for a tokenizer the host already has.
class FunctionUsageBroker(IUsageBroker):
    def __init__(self, count: Callable[[str], Awaitable[int]]) -> None:
        self._count = count

    async def count_tokens(self, text: str) -> int:
        return await self._count(text)
