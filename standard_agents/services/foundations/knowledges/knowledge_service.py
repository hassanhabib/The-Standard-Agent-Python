# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.knowledges.iknowledge_broker import IKnowledgeBroker
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.services.foundations.knowledges.iknowledge_service import (
    IKnowledgeService)


class KnowledgeService(IKnowledgeService):
    def __init__(
        self,
        knowledge_broker: IKnowledgeBroker,
        logging_broker: ILoggingBroker) -> None:

        self.knowledge_broker = knowledge_broker
        self.logging_broker = logging_broker

    async def retrieve_knowledge(self, query: str) -> list[str]:
        raise NotImplementedError
