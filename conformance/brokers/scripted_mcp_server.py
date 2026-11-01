# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping

from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool


class ScriptedMcpServer(McpBroker):
    """A remote tool server, scripted: its catalog is the tools the vector gave it.

    Every tool is described and every call is counted: routing across servers is certified by
    the owner being called and the bystander not (SPEC.md 4.8 v1.5).
    """

    def __init__(
            self,
            tools: Mapping[str, str],
            schemas: Mapping[str, str] | None = None) -> None:
        self._tools = tools
        self._schemas = schemas if schemas is not None else {}
        self._call_count = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    async def call(self, name: str, arguments_json: str) -> str:
        self._call_count += 1

        return self._tools.get(name, f"[external '{name}' not configured]")

    async def list_tools(self) -> list[McpTool]:
        # A tool the vector gave a schema advertises it; the rest take an open object, as a real
        # server that declares none would.
        return [
            McpTool(name, f"scripted tool {name}", self._schemas.get(name, "{}"))
            for name in self._tools]
