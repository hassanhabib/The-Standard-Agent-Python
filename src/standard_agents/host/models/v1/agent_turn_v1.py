# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass, field

from standard_agents.host.models.v1.tool_exchange_v1 import ToolExchangeV1


@dataclass(frozen=True)
class AgentTurnV1:
    """One past exchange in the caller-owned transcript.

    What was asked, what was answered, and the calls that turn made to be able to answer. A
    caller whose protocol is stateless re-posts the whole conversation on every request. Without
    a per-turn home for the calls, a finished call has nowhere to go but
    AgentRunRequestV1.tool_exchanges, which is this turn's in-flight work; a call replayed there
    is read as evidence for the prompt being asked now.
    """

    prompt: str
    answer: str
    exchanges: tuple[ToolExchangeV1, ...] = field(default=(), kw_only=True)
