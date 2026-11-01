# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker


class GateService:
    """The Gate: screens the raw task, and checks active skill instructions for a contradiction.

    The Gate screens the raw task, so it sees exactly what redaction exists to hide, and it may
    run on a different host than the Brain (SPEC.md 4.6). That redaction is a decoration on the
    classifier below, applied at composition, so this service holds one broker.
    """

    def __init__(
            self,
            *,
            classifier_broker: ClassifierBroker,
            logging_broker: LoggingBroker) -> None:

        self.classifier_broker = classifier_broker
        self.logging_broker = logging_broker

    async def screen(self, input: str) -> str:
        raise NotImplementedError

    async def detect_conflict(self, instructions: str) -> str:
        raise NotImplementedError
