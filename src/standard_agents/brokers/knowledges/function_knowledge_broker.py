# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable, Sequence

from standard_agents.brokers.knowledges.iknowledge_broker import IKnowledgeBroker


# The Custom mode's substrate for knowledge (SPEC.md 4.8). Ranking is the host's to do here: the
# contract is "the passages relevant to this query, best first", and how relevance is computed
# is the broker's concern (4.2, 9).
class FunctionKnowledgeBroker(IKnowledgeBroker):
    def __init__(self, retrieve: Callable[[str], Awaitable[Sequence[str]]]) -> None:
        self._retrieve = retrieve

    async def select_knowledge(self, query: str) -> Sequence[str]:
        return await self._retrieve(query)
