# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod

from standard_agents.models.brokers.mcps.mcp_tool import McpTool


class McpBroker(ABC):
    @abstractmethod
    async def call(self, name: str, arguments_json: str) -> str:
        ...

    @abstractmethod
    async def list_tools(self) -> list[McpTool]:
        """The server's tool catalog (tools/list).

        What makes more than one server composable: a router can only send a name to the server
        that owns it if servers say what they own.
        """
