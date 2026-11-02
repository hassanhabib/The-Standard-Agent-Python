# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRunRequest:
    """What to run: the prompt, and nothing else the protocol needs yet."""

    prompt: str
