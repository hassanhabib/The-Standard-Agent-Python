# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.services.foundations.returns.ireturn_service import IReturnService
from standard_agents.services.foundations.returns.return_service_exceptions import try_catch
from standard_agents.services.foundations.returns.return_service_validations import (
    validate_payload)


# The third way Direction can act: not inside the agent, not outside it, but back to whoever
# asked. Returning has no resource to reach, so this foundation holds only its logging broker.
class ReturnService(IReturnService):
    def __init__(self, logging_broker: ILoggingBroker) -> None:
        self.logging_broker = logging_broker

    async def return_payload(self, payload: str) -> str:
        async def returning_string_function() -> str:
            validate_payload(payload)

            return payload

        return await try_catch(self.logging_broker, returning_string_function)
