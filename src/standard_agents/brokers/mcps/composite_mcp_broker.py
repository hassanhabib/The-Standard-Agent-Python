# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool


class CompositeMcpBroker(McpBroker):
    """Many MCP servers behind the one seam the agent already speaks.

    A call routes to the server whose catalog owns the name; when two servers claim the same
    name, the first registered wins, deterministic, and the same precedence internal tools
    already have over external ones. Catalogs are discovered lazily and cached per server on
    success only, so a server that is down at first use is asked again rather than remembered as
    empty.
    """

    def __init__(self, brokers: Iterable[McpBroker]) -> None:
        self._brokers: list[McpBroker] = list(brokers)
        self._catalogs: list[list[McpTool] | None] = [None] * len(self._brokers)
        self._discovery_lock = asyncio.Lock()

    async def call(self, name: str, arguments_json: str) -> str:
        owner = await self._resolve(name)

        return (
            f"[external '{name}' not configured]" if owner is None
            else await owner.call(name, arguments_json))

    async def list_tools(self) -> list[McpTool]:
        await self._discover()

        # First-registered wins here too, so the union a caller sees is the union the router
        # routes by.
        seen: set[str] = set()
        union: list[McpTool] = []

        for catalog in self._catalogs:
            for tool in catalog or []:
                if tool.name not in seen:
                    seen.add(tool.name)
                    union.append(tool)

        return union

    async def _resolve(self, name: str) -> McpBroker | None:
        await self._discover()

        for broker, catalog in zip(self._brokers, self._catalogs):
            if catalog is not None and any(tool.name == name for tool in catalog):
                return broker

        return None

    async def _discover(self) -> None:
        if all(catalog is not None for catalog in self._catalogs):
            return

        async with self._discovery_lock:
            for index in range(len(self._brokers)):
                if self._catalogs[index] is not None:
                    continue

                try:
                    self._catalogs[index] = await self._brokers[index].list_tools()
                except Exception:
                    # A server unreachable at discovery keeps its slot empty and is asked again
                    # on the next call: its outage must not take the other servers' tools with
                    # it, and must not be cached as "has no tools".
                    pass
