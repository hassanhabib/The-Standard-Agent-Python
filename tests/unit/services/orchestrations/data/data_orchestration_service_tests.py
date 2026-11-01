# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

from xeptions import Xeption
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.foundations.knowledges.iknowledge_service import (
    IKnowledgeService)
from standard_agents.services.foundations.memories.imemory_service import IMemoryService
from standard_agents.services.foundations.skills.iskill_service import ISkillService
from standard_agents.services.orchestrations.data.data_orchestration_service import (
    DataOrchestrationService)


class DataOrchestrationServiceTests:
    def setup_method(self) -> None:
        self.skill_service_mock = create_autospec(ISkillService, instance=True)
        self.memory_service_mock = create_autospec(IMemoryService, instance=True)
        self.knowledge_service_mock = create_autospec(IKnowledgeService, instance=True)
        self.logging_broker_mock = create_autospec(ILoggingBroker, instance=True)
        self.tool_catalog = "- " + self.create_random_string()

        self.data_orchestration_service = DataOrchestrationService(
            skill_service=self.skill_service_mock,
            memory_service=self.memory_service_mock,
            knowledge_service=self.knowledge_service_mock,
            logging_broker=self.logging_broker_mock,
            tool_catalog=self.tool_catalog)

    @staticmethod
    def create_random_string() -> str:
        return uuid.uuid4().hex

    @classmethod
    def create_random_context(cls) -> AgentContext:
        return AgentContext(
            prompt=cls.create_random_string(),
            observations=(cls.create_random_string(),))

    def assert_logged_once(self, log_method_name: str, expected_exception: Xeption) -> None:
        assert len(self.logging_broker_mock.mock_calls) == 1
        logged_method_name, logged_arguments, _ = self.logging_broker_mock.mock_calls[0]
        assert logged_method_name == log_method_name
        assert expected_exception.same_exception_as(logged_arguments[0])
