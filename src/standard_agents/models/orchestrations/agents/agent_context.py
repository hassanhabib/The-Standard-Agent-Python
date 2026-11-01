# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


# The one thing the three natures pass around the loop. Frozen, so every nature returns a new
# context rather than changing the one it was handed (dataclasses.replace is C#'s "with").
@dataclass(frozen=True)
class AgentContext:
    prompt: str = ""

    # Data: what the agent has this turn. Memories and knowledge are recalled fresh every turn;
    # observations are what Direction saw, and they accumulate across the run.
    system_prompt: str = ""
    memories: tuple[str, ...] = ()
    knowledge: tuple[str, ...] = ()
    observations: tuple[str, ...] = ()

    # Decision: what the brain chose, in the loop's terms.
    direction_type: str = ""
    payload: str = ""
    narration: str = ""
    raw_reply: str = ""

    # Direction: what was done, and whether the run goes on.
    result: str = ""
    status: AgentStatus = AgentStatus.WORKING
