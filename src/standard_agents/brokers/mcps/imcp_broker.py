# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod

from standard_agents.models.brokers.mcps.remote_tool import RemoteTool


# Out across the boundary: a remote tool server (SPEC.md 4.1). Direction routes here any act the
# agent does not own.
class IMcpBroker(ABC):
    @abstractmethod
    async def call(self, name: str, input: str) -> str: ...

    @abstractmethod
    async def list_tools(self) -> list[RemoteTool]: ...
