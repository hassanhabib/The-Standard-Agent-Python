# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.classifiers.iclassifier_broker import IClassifierBroker
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.services.foundations.gates.gate_service_exceptions import try_catch
from standard_agents.services.foundations.gates.gate_service_validations import validate_text
from standard_agents.services.foundations.gates.igate_service import IGateService


class GateService(IGateService):
    def __init__(
        self,
        classifier_broker: IClassifierBroker,
        logging_broker: ILoggingBroker) -> None:

        self.classifier_broker = classifier_broker
        self.logging_broker = logging_broker

    async def screen(self, gate_prompt: str, input: str) -> str:
        async def returning_string_function() -> str:
            validate_text(input)
            verdict = await self.classifier_broker.classify(gate_prompt, input)

            return verdict.strip()

        return await try_catch(self.logging_broker, returning_string_function)
