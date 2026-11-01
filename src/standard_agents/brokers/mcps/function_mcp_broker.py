# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from standard_agents.brokers.mcps.imcp_broker import IMcpBroker
from standard_agents.models.brokers.mcps.remote_tool import RemoteTool


# The Custom mode: the host's own function answers acts routed outward. It offers no catalog;
# a host that wants its remote tools advertised supplies a whole broker instead.
class FunctionMcpBroker(IMcpBroker):
    def __init__(self, call: Callable[[str, str], Awaitable[str]]) -> None:
        self.call_function = call

    async def call(self, name: str, input: str) -> str:
        return await self.call_function(name, input)

    async def list_tools(self) -> list[RemoteTool]:
        return []
