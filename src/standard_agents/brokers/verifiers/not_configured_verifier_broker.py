# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker


# No Judge configured: every answer is accepted, exactly as if the Judge were absent.
class NotConfiguredVerifierBroker(IVerifierBroker):
    async def verify(self, system_prompt: str, task: str, candidate: str) -> str:
        return "1.0"
