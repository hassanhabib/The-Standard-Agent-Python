# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

from xeptions import Xeption
from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.services.foundations.brains.brain_service import BrainService


# The setup half of the BrainService tests; the Logic, Validations and Exceptions files each
# extend it, the way the C# partial test classes share one constructor.
class BrainServiceTests:
    def setup_method(self) -> None:
        self.generator_broker_mock = create_autospec(IGeneratorBroker, instance=True)
        self.logging_broker_mock = create_autospec(ILoggingBroker, instance=True)

        self.brain_service = BrainService(
            generator_broker=self.generator_broker_mock,
            logging_broker=self.logging_broker_mock)

    @staticmethod
    def create_random_string() -> str:
        return uuid.uuid4().hex

    def assert_logged_once(self, log_method_name: str, expected_exception: Xeption) -> None:
        assert len(self.logging_broker_mock.mock_calls) == 1
        logged_method_name, logged_arguments, _ = self.logging_broker_mock.mock_calls[0]
        assert logged_method_name == log_method_name
        assert expected_exception.same_exception_as(logged_arguments[0])
