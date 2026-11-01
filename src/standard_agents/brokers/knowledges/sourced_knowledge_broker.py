# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult


class SourcedKnowledgeBroker(ABC):
    """The knowledge seam for a source that can say where a passage came from (SPEC.md 4.1).

    It sits beside KnowledgeBroker rather than replacing it: a source implements either, and a
    plain one keeps working, lifted to passages with no known origin.
    """

    @abstractmethod
    async def select_sourced_knowledge(self, query: str) -> Sequence[KnowledgeResult]:
        ...
