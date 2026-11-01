# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence

from standard_agents.brokers.files.file_broker import FileBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.knowledges.sourced_knowledge_broker import SourcedKnowledgeBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult


class KnowledgeService:
    """What the agent knows that is relevant to a task, from a broker or a folder of files."""

    def __init__(
            self,
            *,
            logging_broker: LoggingBroker,
            knowledge_broker: KnowledgeBroker | None = None,
            sourced_knowledge_broker: SourcedKnowledgeBroker | None = None,
            file_broker: FileBroker | None = None,
            knowledge_path: str = "",
            search_pattern: str = "",
            max_results: int = 0,
            minimum_score: float = 0.0) -> None:

        self.knowledge_broker = knowledge_broker
        self.sourced_knowledge_broker = sourced_knowledge_broker
        self.file_broker = file_broker
        self.knowledge_path = knowledge_path
        self.search_pattern = search_pattern
        self.max_results = max_results
        self.minimum_score = minimum_score
        self.logging_broker = logging_broker

    async def retrieve_knowledge(self, query: str) -> Sequence[str]:
        raise NotImplementedError

    async def retrieve_sourced_knowledge(self, query: str) -> Sequence[KnowledgeResult]:
        raise NotImplementedError
