# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.services.foundations.returns.return_service import ReturnService


class ReturnServiceTests:
    def setup_method(self) -> None:
        self.logging_broker_mock = create_autospec(ILoggingBroker, instance=True)
        self.return_service = ReturnService(logging_broker=self.logging_broker_mock)

    @staticmethod
    def create_random_string() -> str:
        return uuid.uuid4().hex

    def assert_logged_once(self, log_method_name: str, expected_exception: Xeption) -> None:
        assert len(self.logging_broker_mock.mock_calls) == 1
        logged_method_name, logged_arguments, _ = self.logging_broker_mock.mock_calls[0]
        assert logged_method_name == log_method_name
        assert expected_exception.same_exception_as(logged_arguments[0])
