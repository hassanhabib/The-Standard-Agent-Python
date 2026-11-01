# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.redactions.redaction_broker import RedactionBroker


# The Gate screens the raw task, so it sees exactly what redaction exists to hide, and it may
# run on a different host than the Brain (SPEC.md 4.6).
#
# The verdict is rehydrated on the way back: a classification carries no data, but a refusal
# reason quotes the input, and that reason is read by a human.
class RedactingClassifierBroker(ClassifierBroker):
    def __init__(
        self,
        classifier_broker: ClassifierBroker,
        redaction_broker: RedactionBroker) -> None:

        self._classifier_broker = classifier_broker
        self._redaction_broker = redaction_broker

    async def classify(self, input: str) -> str:
        vault: dict[str, str] = {}

        verdict = await self._classifier_broker.classify(
            self._redaction_broker.redact(input, vault))

        return self._redaction_broker.rehydrate(verdict, vault)

    async def assess(self, system_prompt: str, input: str) -> str:
        vault: dict[str, str] = {}

        verdict = await self._classifier_broker.assess(
            system_prompt,
            self._redaction_broker.redact(input, vault))

        return self._redaction_broker.rehydrate(verdict, vault)
