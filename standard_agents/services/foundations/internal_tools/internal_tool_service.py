# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.tools.itool_broker import IToolBroker
from standard_agents.services.foundations.internal_tools.iinternal_tool_service import (
    IInternalToolService)


class InternalToolService(IInternalToolService):
    def __init__(
        self,
        tool_broker: IToolBroker,
        logging_broker: ILoggingBroker) -> None:

        self.tool_broker = tool_broker
        self.logging_broker = logging_broker

    async def handles(self, name: str) -> bool:
        raise NotImplementedError
