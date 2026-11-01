# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.knowledges.iknowledge_broker import IKnowledgeBroker


class NotConfiguredKnowledgeBroker(IKnowledgeBroker):
    async def select_knowledge(self, query: str) -> list[str]:
        return []
