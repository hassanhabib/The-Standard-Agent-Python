# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.foundations.brains.ibrain_service import IBrainService
from standard_agents.services.foundations.gates.igate_service import IGateService
from standard_agents.services.foundations.judges.ijudge_service import IJudgeService
from standard_agents.services.orchestrations.decision.decision_orchestration_service import (
    DecisionOrchestrationService)


class DecisionOrchestrationServiceTests:
    def setup_method(self) -> None:
        self.brain_service_mock = create_autospec(IBrainService, instance=True)
        self.gate_service_mock = create_autospec(IGateService, instance=True)
        self.judge_service_mock = create_autospec(IJudgeService, instance=True)
        self.logging_broker_mock = create_autospec(ILoggingBroker, instance=True)

        self.decision_orchestration_service = DecisionOrchestrationService(
            brain_service=self.brain_service_mock,
            gate_service=self.gate_service_mock,
            judge_service=self.judge_service_mock,
            logging_broker=self.logging_broker_mock)

    @staticmethod
    def create_random_string() -> str:
        return uuid.uuid4().hex

    @classmethod
    def create_random_context(cls) -> AgentContext:
        return AgentContext(
            prompt=cls.create_random_string(),
            system_prompt=cls.create_random_string(),
            memories=(cls.create_random_string(),),
            knowledge=(cls.create_random_string(),),
            observations=(cls.create_random_string(),))

    # What the brain is shown: the task, then everything the agent has and has seen, written out
    # here by hand so the test pins the shape rather than recomputing it.
    @staticmethod
    def create_user_message(context: AgentContext) -> str:
        return (
            f"Task: {context.prompt}\n\n"
            + "Observations so far:\n"
            + f"- {context.memories[0]}\n"
            + f"- {context.knowledge[0]}\n"
            + f"- {context.observations[0]}\n")

    def assert_logged_once(self, log_method_name: str, expected_exception: Xeption) -> None:
        error_calls = [
            logged_call for logged_call in self.logging_broker_mock.mock_calls
            if logged_call[0] in ("log_error", "log_critical")
        ]

        assert len(error_calls) == 1
        logged_method_name, logged_arguments, _ = error_calls[0]
        assert logged_method_name == log_method_name
        assert expected_exception.same_exception_as(logged_arguments[0])
