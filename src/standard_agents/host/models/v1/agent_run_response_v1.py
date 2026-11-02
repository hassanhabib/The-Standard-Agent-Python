# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.host.models.v1.failure_v1 import FailureV1
from standard_agents.host.models.v1.pending_effect_v1 import PendingEffectV1


@dataclass(frozen=True)
class AgentRunResponseV1:
    """How the run ended, in protocol form: the wire form of AgentOutcome, version 1.

    Status travels beside the result because only Responded makes the result an answer, and the
    pending effect travels beside them because a stateless caller that cannot see the act the
    run is waiting on cannot perform it, approve it, or answer it. The failure travels beside
    them because a run that stopped without an answer says why as a code, and a caller that can
    only read the sentence cannot decide whether to retry. None on every run that answered, so a
    caller that never reads it sees the response it always saw.
    """

    result: str
    status: str
    pending_effect: PendingEffectV1 | None
    failure: FailureV1 | None = None
