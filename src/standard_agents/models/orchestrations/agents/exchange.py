# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


# One call a turn made, and what came back (SPEC.md 3.2). replayed is true exactly when a run-once
# ledger answered the call instead of the tool, and defaults to false.
@dataclass(frozen=True)
class Exchange:
    call_id: str
    tool_name: str
    arguments: str
    result: str
    replayed: bool = False
