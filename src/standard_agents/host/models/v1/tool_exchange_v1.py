# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolExchangeV1:
    """A tool call the caller executed and is answering.

    The call id is the whole point: the model that asked for the call expects the result back
    naming that call, and an id the host invents is one the model cannot match.
    """

    call_id: str
    tool_name: str
    arguments_json: str
    result: str
