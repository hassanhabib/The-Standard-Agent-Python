# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.mcps.imcp_broker import IMcpBroker
from standard_agents.services.foundations.external_tools.external_tool_service_exceptions import (
    try_catch)
from standard_agents.services.foundations.external_tools.external_tool_service_validations import (
    validate_name)
from standard_agents.services.foundations.external_tools.iexternal_tool_service import (
    IExternalToolService)


# Out across the boundary (SPEC.md 4.2): an act the agent does not own goes to a remote tool
# server, and what comes back is Data like any other result.
class ExternalToolService(IExternalToolService):
    def __init__(
        self,
        mcp_broker: IMcpBroker,
        logging_broker: ILoggingBroker) -> None:

        self.mcp_broker = mcp_broker
        self.logging_broker = logging_broker

    async def call(self, name: str, input: str) -> str:
        async def returning_string_function() -> str:
            validate_name(name)

            return await self.mcp_broker.call(name, input)

        return await try_catch(self.logging_broker, returning_string_function)
