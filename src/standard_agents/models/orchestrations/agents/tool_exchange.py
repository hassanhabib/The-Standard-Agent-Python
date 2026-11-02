# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolExchange:
    """One native tool call and its result, kept together.

    The id is the whole point: a hosted model that asked for a call expects the answer back as
    a tool message naming that call, which is the one thing the text protocol cannot express
    (SPEC.md 6).
    """

    call_id: str
    tool_name: str
    arguments_json: str
    result: str

    # Whether the run-once ledger answered this call rather than the tool (SPEC.md 3.2, v1.14).
    # False by default, so an exchange recorded before this existed reads as a call that ran.
    replayed: bool = field(default=False, kw_only=True)
