# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.services.foundations.returns.ireturn_service import IReturnService


# The third way Direction can act: not inside the agent, not outside it, but back to whoever
# asked. Returning has no resource to reach, so this foundation holds only its logging broker.
class ReturnService(IReturnService):
    def __init__(self, logging_broker: ILoggingBroker) -> None:
        self.logging_broker = logging_broker

    async def return_payload(self, payload: str) -> str:
        raise NotImplementedError
