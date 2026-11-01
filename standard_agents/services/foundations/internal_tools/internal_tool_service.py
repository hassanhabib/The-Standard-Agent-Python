# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.tools.itool_broker import IToolBroker
from standard_agents.services.foundations.internal_tools.iinternal_tool_service import (
    IInternalToolService)
from standard_agents.services.foundations.internal_tools.internal_tool_service_exceptions import (
    try_catch_returning_boolean)
from standard_agents.services.foundations.internal_tools.internal_tool_service_validations import (
    validate_name)


class InternalToolService(IInternalToolService):
    def __init__(
        self,
        tool_broker: IToolBroker,
        logging_broker: ILoggingBroker) -> None:

        self.tool_broker = tool_broker
        self.logging_broker = logging_broker

    async def handles(self, name: str) -> bool:
        async def returning_boolean_function() -> bool:
            validate_name(name)

            return await self.tool_broker.has(name)

        return await try_catch_returning_boolean(self.logging_broker, returning_boolean_function)

    async def run(self, name: str, input: str) -> str:
        return await self.tool_broker.run(name, input)
