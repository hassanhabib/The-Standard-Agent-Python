# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker

# (1.0).ToString(CultureInfo.InvariantCulture) writes the shortest round-trip form: "1".
_PASSING_SCORE = "1"


class NotConfiguredVerifierBroker(IVerifierBroker):
    async def verify(self, task: str, candidate: str) -> str:
        return _PASSING_SCORE
