# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class McpTool:
    """One tool an MCP server offers, as its catalog describes it.

    The name a call must use, the description that would advertise it, and the JSON Schema of
    the arguments it takes. What a tool takes is part of what advertises it; a server that
    declares no schema takes an open object.
    """

    name: str
    description: str
    input_schema_json: str = "{}"
