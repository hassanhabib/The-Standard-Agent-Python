# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import json
from collections.abc import Sequence

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.mcps import mcp_json
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool

# The one argument plain text travels as, for a tool that declared no schema of its own.
_INPUT_ARGUMENT_NAME = "input"


class ExternalToolService:
    """The tools the agent reaches on MCP servers, through an MCP broker."""

    def __init__(self, *, mcp_broker: McpBroker, logging_broker: LoggingBroker) -> None:
        self.mcp_broker = mcp_broker
        self.logging_broker = logging_broker

    async def call(self, name: str, input: str) -> str:
        return await self.mcp_broker.call(name, _to_arguments_json(input))

    async def retrieve_tools(self) -> Sequence[McpTool]:
        """The remote tools the configured servers offer, in business language.

        What the agent may reach for, localized and categorized like every other foundation
        answer. A server that cannot be asked is a dependency failure this service names, never
        an empty catalog.
        """
        raise NotImplementedError


def _to_arguments_json(input: str) -> str:
    """The JSON object of arguments the wire takes.

    A native call already wrote one, and it goes over exactly as written; the text protocol
    produces plain text, which travels as the one argument a schema-less tool understands.
    Forcing every call into that one argument was what left typed, multi-property tools
    uncallable (principal review 2026-09-04, F-03).
    """
    if _is_json_object(input):
        return input

    return mcp_json.to_json_string({_INPUT_ARGUMENT_NAME: input})


def _is_json_object(input: str) -> bool:
    try:
        return isinstance(mcp_json.parse(input), dict)
    except json.JSONDecodeError:
        return False
