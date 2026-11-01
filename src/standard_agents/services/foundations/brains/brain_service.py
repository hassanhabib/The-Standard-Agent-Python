# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.services.foundations.brains.brain_service_exceptions import try_catch
from standard_agents.services.foundations.brains.brain_service_validations import (
    validate_user_prompt)
from standard_agents.services.foundations.brains.ibrain_service import IBrainService


class BrainService(IBrainService):
    def __init__(
        self,
        generator_broker: IGeneratorBroker,
        logging_broker: ILoggingBroker) -> None:

        self.generator_broker = generator_broker
        self.logging_broker = logging_broker

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        async def returning_string_function() -> str:
            validate_user_prompt(user_prompt)

            return await self.generator_broker.generate(system_prompt, user_prompt)

        return await try_catch(self.logging_broker, returning_string_function)
