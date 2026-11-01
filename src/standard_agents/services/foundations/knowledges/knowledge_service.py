# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.knowledges.iknowledge_broker import IKnowledgeBroker
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.services.foundations.knowledges.iknowledge_service import (
    IKnowledgeService)
from standard_agents.services.foundations.knowledges.knowledge_service_exceptions import (
    try_catch)
from standard_agents.services.foundations.knowledges.knowledge_service_validations import (
    validate_query)


class KnowledgeService(IKnowledgeService):
    def __init__(
        self,
        knowledge_broker: IKnowledgeBroker,
        logging_broker: ILoggingBroker) -> None:

        self.knowledge_broker = knowledge_broker
        self.logging_broker = logging_broker

    async def retrieve_knowledge(self, query: str) -> list[str]:
        async def returning_list_function() -> list[str]:
            validate_query(query)

            return await self.knowledge_broker.select_knowledge(query)

        return await try_catch(self.logging_broker, returning_list_function)
