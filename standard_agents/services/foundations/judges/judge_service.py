# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker
from standard_agents.models.foundations.judges.judgement import Judgement
from standard_agents.services.foundations.judges.ijudge_service import IJudgeService


class JudgeService(IJudgeService):
    def __init__(
        self,
        verifier_broker: IVerifierBroker,
        logging_broker: ILoggingBroker) -> None:

        self.verifier_broker = verifier_broker
        self.logging_broker = logging_broker

    async def evaluate(self, task: str, candidate: str) -> Judgement:
        raise NotImplementedError
