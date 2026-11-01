# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass, field

from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.foundations.usages.agent_usage import AgentUsage


@dataclass(frozen=True)
class AgentStreamEvent:
    type: AgentStreamEventType
    content: str

    # The run's usage so far, on a USAGE event, and nothing on every other kind. Carried whole
    # rather than only as the number in content, because a count is either reported or
    # estimated (SPEC.md 3.4) and the text cannot say which.
    usage: AgentUsage | None = field(default=None, kw_only=True)
