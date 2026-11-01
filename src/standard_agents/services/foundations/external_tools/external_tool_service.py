# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.mcps.imcp_broker import IMcpBroker
from standard_agents.services.foundations.external_tools.iexternal_tool_service import (
    IExternalToolService)


class ExternalToolService(IExternalToolService):
    def __init__(
        self,
        mcp_broker: IMcpBroker,
        logging_broker: ILoggingBroker) -> None:

        self.mcp_broker = mcp_broker
        self.logging_broker = logging_broker

    async def call(self, name: str, input: str) -> str:
        raise NotImplementedError
