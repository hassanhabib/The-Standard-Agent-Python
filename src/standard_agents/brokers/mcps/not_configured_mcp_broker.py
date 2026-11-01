# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.mcps.imcp_broker import IMcpBroker
from standard_agents.models.brokers.mcps.remote_tool import RemoteTool


# No remote tool server configured. An act routed outward is answered with that fact, so it
# becomes an observation the brain can recover from rather than a failure of the run.
class NotConfiguredMcpBroker(IMcpBroker):
    async def call(self, name: str, input: str) -> str:
        return f"[external '{name}' not configured]"

    async def list_tools(self) -> list[RemoteTool]:
        return []
