# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from standard_agents.i_agent import IAgent


# One agent a registry offers: the name a handoff must use, the description that advertises it
# (the same opt-in a tool's description is: no description, no advertisement), and the agent
# itself, already composed by whoever registered it.
@dataclass(frozen=True)
class RegisteredAgent:
    name: str
    description: str
    agent: IAgent
