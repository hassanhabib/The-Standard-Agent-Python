# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import copy
import dataclasses
from unittest.mock import call

from tests.unit.services.orchestrations.data.data_orchestration_service_tests import (
    DataOrchestrationServiceTests)


class TestDataOrchestrationServiceLogicRecall(DataOrchestrationServiceTests):
    def test_should_recall_skills_memories_and_knowledge(self) -> None:
        # given
        input_context = self.create_random_context()
        random_instructions = self.create_random_string()
        returned_skills = random_instructions + "\n{{tools}}"
        returned_memories = [self.create_random_string()]
        returned_knowledge = [self.create_random_string(), self.create_random_string()]

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            system_prompt=random_instructions + "\n" + self.tool_catalog,
            memories=tuple(returned_memories),
            knowledge=tuple(returned_knowledge))

        self.skill_service_mock.retrieve_all_skills.return_value = returned_skills
        self.memory_service_mock.retrieve_all_memories.return_value = returned_memories
        self.knowledge_service_mock.retrieve_knowledge.return_value = returned_knowledge

        # when
        actual_context = asyncio.run(self.data_orchestration_service.recall(input_context))

        # then
        assert actual_context == expected_context
        assert self.skill_service_mock.mock_calls == [call.retrieve_all_skills()]
        assert self.memory_service_mock.mock_calls == [call.retrieve_all_memories()]

        assert self.knowledge_service_mock.mock_calls == [
            call.retrieve_knowledge(input_context.prompt)
        ]

        assert self.logging_broker_mock.mock_calls == []
