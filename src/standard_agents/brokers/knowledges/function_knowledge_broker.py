# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from standard_agents.brokers.knowledges.iknowledge_broker import IKnowledgeBroker


class FunctionKnowledgeBroker(IKnowledgeBroker):
    def __init__(self, select_knowledge: Callable[[str], Awaitable[list[str]]]) -> None:
        self.select_knowledge_function = select_knowledge

    async def select_knowledge(self, query: str) -> list[str]:
        return await self.select_knowledge_function(query)
