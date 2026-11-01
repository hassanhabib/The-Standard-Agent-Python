# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.mcps.imcp_broker import IMcpBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool


class NotConfiguredMcpBroker(IMcpBroker):
    async def call(self, name: str, arguments_json: str) -> str:
        return f"[external '{name}' not configured]"

    async def list_tools(self) -> list[McpTool]:
        return []
