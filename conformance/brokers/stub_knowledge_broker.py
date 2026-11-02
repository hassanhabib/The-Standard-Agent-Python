# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker


class StubKnowledgeBroker(KnowledgeBroker):
    """Knowledge that retrieves nothing, so no vector is disturbed by retrieval existing."""

    async def select_knowledge(self, query: str) -> Sequence[str]:
        return []
