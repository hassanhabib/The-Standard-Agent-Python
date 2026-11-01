# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.services.coordinations.runs.run_coordination_service import (
    RunCoordinationService)
from standard_agents.services.orchestrations.data.idata_orchestration_service import (
    IDataOrchestrationService)
from standard_agents.services.orchestrations.decision.idecision_orchestration_service import (
    IDecisionOrchestrationService)
from standard_agents.services.orchestrations.direction.idirection_orchestration_service import (
    IDirectionOrchestrationService)


class RunCoordinationServiceTests:
    def setup_method(self) -> None:
        self.data_orchestration_service_mock = create_autospec(
            IDataOrchestrationService, instance=True)

        self.decision_orchestration_service_mock = create_autospec(
            IDecisionOrchestrationService, instance=True)

        self.direction_orchestration_service_mock = create_autospec(
            IDirectionOrchestrationService, instance=True)

        self.logging_broker_mock = create_autospec(ILoggingBroker, instance=True)
        self.run_coordination_service = self.create_run_coordination_service()

    def create_run_coordination_service(self, max_turns: int = 7) -> RunCoordinationService:
        return RunCoordinationService(
            data_orchestration_service=self.data_orchestration_service_mock,
            decision_orchestration_service=self.decision_orchestration_service_mock,
            direction_orchestration_service=self.direction_orchestration_service_mock,
            logging_broker=self.logging_broker_mock,
            max_turns=max_turns)

    @staticmethod
    def create_random_string() -> str:
        return uuid.uuid4().hex

    # A distinct context per step of a turn, so a call made with the wrong one fails the test:
    # the order is proven by what each nature is handed, not by counting calls.
    @classmethod
    def create_random_context(
        cls,
        prompt: str,
        status: AgentStatus = AgentStatus.WORKING) -> AgentContext:

        return AgentContext(
            prompt=prompt,
            payload=cls.create_random_string(),
            result=cls.create_random_string(),
            status=status)

    def assert_logged_once(self, log_method_name: str, expected_exception: Xeption) -> None:
        error_calls = [
            logged_call for logged_call in self.logging_broker_mock.mock_calls
            if logged_call[0] in ("log_error", "log_critical")
        ]

        assert len(error_calls) == 1
        logged_method_name, logged_arguments, _ = error_calls[0]
        assert logged_method_name == log_method_name
        assert expected_exception.same_exception_as(logged_arguments[0])
