# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.tools.itool import ITool
from standard_agents.brokers.tools.itool_broker import IToolBroker


# Tool names are matched without regard to case. Composition keys the tools by their lower-case
# name, so the broker only ever looks one up.
class ToolBroker(IToolBroker):
    def __init__(self, tools: dict[str, ITool]) -> None:
        self.tools = tools

    async def has(self, name: str) -> bool:
        return name.lower() in self.tools

    async def run(self, name: str, input: str) -> str:
        return await self.tools[name.lower()].execute(input)
