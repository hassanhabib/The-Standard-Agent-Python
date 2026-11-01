# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable, Sequence

from standard_agents.brokers.knowledges.sourced_knowledge_broker import SourcedKnowledgeBroker
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult


class FunctionSourcedKnowledgeBroker(SourcedKnowledgeBroker):
    """The Custom mode's substrate for sourced knowledge (SPEC.md 4.8).

    The host's own retrieval, ranked by the host, saying where each passage came from.
    """

    def __init__(self, retrieve: Callable[[str], Awaitable[Sequence[KnowledgeResult]]]) -> None:
        self._retrieve = retrieve

    async def select_sourced_knowledge(self, query: str) -> Sequence[KnowledgeResult]:
        return await self._retrieve(query)
