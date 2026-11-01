# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.tools.tool_broker import ToolBroker


class InternalToolService:
    """The tools the agent carries in process, reached through a tool broker."""

    def __init__(self, *, tool_broker: ToolBroker, logging_broker: LoggingBroker) -> None:
        self.tool_broker = tool_broker
        self.logging_broker = logging_broker

    async def handles(self, name: str) -> bool:
        return await self.tool_broker.has(name)

    async def run(self, name: str, input: str) -> str:
        return await self.tool_broker.run(name, input)

    async def compensate(self, name: str, input: str, outcome: str) -> str:
        """Undoes what a tool did, where the tool knows how (SPEC.md 4.9).

        Returns what was done, or an empty string when the tool declared no way back.
        """
        raise NotImplementedError
