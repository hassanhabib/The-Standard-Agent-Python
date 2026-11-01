# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.redactions.iredaction_broker import IRedactionBroker
from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker


class RedactingVerifierBroker(IVerifierBroker):
    def __init__(
        self,
        verifier_broker: IVerifierBroker,
        redaction_broker: IRedactionBroker) -> None:

        self._verifier_broker = verifier_broker
        self._redaction_broker = redaction_broker

    # One vault across both, so the same value redacts to the same token in the task and in the
    # answer; otherwise the Judge cannot tell that the answer is about the person the task asked
    # about, and it scores a mismatch that is not there.
    #
    # The verdict is rehydrated because a rejection's reason quotes the answer back, and that
    # reason becomes the revision feedback the Brain reads (SPEC.md 4.3).
    async def verify(self, task: str, candidate: str) -> str:
        vault: dict[str, str] = {}

        verdict = await self._verifier_broker.verify(
            self._redaction_broker.redact(task, vault),
            self._redaction_broker.redact(candidate, vault))

        return self._redaction_broker.rehydrate(verdict, vault)
