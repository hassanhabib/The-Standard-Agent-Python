# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.foundations.external_tools.iexternal_tool_service import (
    IExternalToolService)
from standard_agents.services.foundations.internal_tools.iinternal_tool_service import (
    IInternalToolService)
from standard_agents.services.foundations.returns.ireturn_service import IReturnService
from standard_agents.services.orchestrations.direction.direction_orchestration_service import (
    DirectionOrchestrationService)


class DirectionOrchestrationServiceTests:
    def setup_method(self) -> None:
        self.internal_tool_service_mock = create_autospec(IInternalToolService, instance=True)
        self.external_tool_service_mock = create_autospec(IExternalToolService, instance=True)
        self.return_service_mock = create_autospec(IReturnService, instance=True)
        self.logging_broker_mock = create_autospec(ILoggingBroker, instance=True)

        self.direction_orchestration_service = DirectionOrchestrationService(
            internal_tool_service=self.internal_tool_service_mock,
            external_tool_service=self.external_tool_service_mock,
            return_service=self.return_service_mock,
            logging_broker=self.logging_broker_mock)

    @staticmethod
    def create_random_string() -> str:
        return uuid.uuid4().hex

    @classmethod
    def create_random_context(cls, direction_type: str) -> AgentContext:
        return AgentContext(
            prompt=cls.create_random_string(),
            observations=(cls.create_random_string(),),
            direction_type=direction_type,
            payload=cls.create_random_string())

    def assert_logged_once(self, log_method_name: str, expected_exception: Xeption) -> None:
        error_calls = [
            logged_call for logged_call in self.logging_broker_mock.mock_calls
            if logged_call[0] in ("log_error", "log_critical")
        ]

        assert len(error_calls) == 1
        logged_method_name, logged_arguments, _ = error_calls[0]
        assert logged_method_name == log_method_name
        assert expected_exception.same_exception_as(logged_arguments[0])
