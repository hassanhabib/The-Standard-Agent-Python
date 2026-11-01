# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.services.foundations.brains.ibrain_service import IBrainService


class BrainService(IBrainService):
    def __init__(
        self,
        generator_broker: IGeneratorBroker,
        logging_broker: ILoggingBroker) -> None:

        self.generator_broker = generator_broker
        self.logging_broker = logging_broker

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError
