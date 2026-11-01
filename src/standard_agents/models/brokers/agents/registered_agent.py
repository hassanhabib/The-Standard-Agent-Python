# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from standard_agents.agent import Agent


@dataclass(frozen=True)
class RegisteredAgent:
    """One agent a registry offers.

    The name a handoff must use, the description that advertises it (the same opt-in a tool's
    description is: no description, no advertisement), and the agent itself, already composed
    by whoever registered it.
    """

    name: str
    description: str
    agent: Agent
