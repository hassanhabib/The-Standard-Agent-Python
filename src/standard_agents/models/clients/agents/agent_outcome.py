# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass, field

from standard_agents.models.clients.agents.agent_failure import AgentFailure
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect


@dataclass(frozen=True)
class AgentOutcome:
    """How a run ended, and what it produced.

    result: the answer, or the reason there is not one.
    status: which way it ended. RESPONDED is the only one that makes the result an answer.
    Every other ending produces prose about why: a run out of turns says so, with WORKING
    because it stopped mid-work, and never hands back a tool's raw output as though it were an
    answer.
    pending_effect: the act the run is waiting on, when it ended waiting (a caller's tool call,
    or an act held for approval). None when the run is not waiting on anything.
    """

    result: str
    status: AgentStatus
    pending_effect: AgentEffect | None = None

    # Why the run stopped without an answer, as a code a caller can switch on (SPEC.md 3.6,
    # v1.14). None when the run answered, asked, refused or is waiting for approval: none of
    # those is a stop without an answer.
    failure: AgentFailure | None = field(default=None, kw_only=True)
