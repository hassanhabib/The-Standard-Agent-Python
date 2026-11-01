# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.agents.turn import Turn


# The single carrier that threads the loop (SPEC.md 3.2). All of it is Data; the groups say
# which nature last writes each field. Frozen, so a nature returns an updated copy and never
# changes the one it was handed: dataclasses.replace is the copy-on-write.
@dataclass(frozen=True)
class AgentContext:
    prompt: str = ""

    # Data
    session_id: str | None = None
    history: tuple[Turn, ...] = ()
    system_prompt: str = ""
    observations: tuple[str, ...] = ()
    grounding_sources: tuple[str, ...] = ()

    # Decision
    intent: str = ""
    direction_type: str = ""
    payload: str = ""
    raw_reply: str = ""

    # Direction
    result: str = ""
    status: AgentStatus = AgentStatus.WORKING
