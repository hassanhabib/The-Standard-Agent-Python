# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool


class ExternalToolService:
    """The tools the agent reaches on MCP servers, through an MCP broker."""

    def __init__(self, *, mcp_broker: McpBroker, logging_broker: LoggingBroker) -> None:
        self.mcp_broker = mcp_broker
        self.logging_broker = logging_broker

    async def call(self, name: str, input: str) -> str:
        raise NotImplementedError

    async def retrieve_tools(self) -> Sequence[McpTool]:
        """The remote tools the configured servers offer, in business language.

        What the agent may reach for, localized and categorized like every other foundation
        answer. A server that cannot be asked is a dependency failure this service names, never
        an empty catalog.
        """
        raise NotImplementedError
