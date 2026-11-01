# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.foundations.judges.judgement import Judgement


class JudgeService:
    """Scores a candidate answer as an answer to its task, from the verifier's verdict."""

    def __init__(
            self,
            *,
            verifier_broker: VerifierBroker,
            logging_broker: LoggingBroker) -> None:

        self.verifier_broker = verifier_broker
        self.logging_broker = logging_broker

    async def evaluate(self, task: str, candidate: str) -> Judgement:
        raise NotImplementedError
