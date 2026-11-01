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
    # SPEC.md 4.3: recall sets the system prompt from skills and seeds observations from memory and
    # knowledge. Recall runs every turn, so what is already observed is not observed twice.
    def test_should_recall_skills_and_seed_observations_once(self) -> None:
        # given
        recalled_before = self.create_random_string()
        input_context = self.create_random_context()

        input_context = dataclasses.replace(
            input_context,
            observations=input_context.observations + (recalled_before,))

        random_instructions = self.create_random_string()
        returned_skills = random_instructions + "\n{{tools}}"
        new_memory = self.create_random_string()
        new_knowledge = self.create_random_string()
        returned_memories = [recalled_before, new_memory]
        returned_knowledge = [new_knowledge, recalled_before]

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            system_prompt=random_instructions + "\n" + self.tool_catalog,
            observations=input_context.observations + (new_memory, new_knowledge))

        self.skill_service_mock.retrieve_skills.return_value = returned_skills
        self.memory_service_mock.retrieve_all_memories.return_value = returned_memories
        self.knowledge_service_mock.retrieve_knowledge.return_value = returned_knowledge

        # when
        actual_context = asyncio.run(self.data_orchestration_service.recall(input_context))

        # then
        assert actual_context == expected_context
        assert self.skill_service_mock.mock_calls == [call.retrieve_skills("")]
        assert self.memory_service_mock.mock_calls == [call.retrieve_all_memories()]

        assert self.knowledge_service_mock.mock_calls == [
            call.retrieve_knowledge(input_context.prompt)
        ]

        assert self.logging_broker_mock.mock_calls == []

    # SPEC.md 4.2: the skill catalog is advertised where Data asks for it, at a skills marker, the
    # way tools are at a tools marker; absent the marker it is never fetched or shown.
    def test_should_recall_the_skill_catalog_where_the_skills_ask_for_it(self) -> None:
        # given
        input_context = self.create_random_context()
        random_instructions = self.create_random_string()
        returned_skills = random_instructions + "\n{{skills}}"
        returned_catalog = "- " + self.create_random_string()

        expected_context = dataclasses.replace(
            copy.deepcopy(input_context),
            system_prompt=random_instructions + "\n" + returned_catalog)

        self.skill_service_mock.retrieve_skills.return_value = returned_skills
        self.skill_service_mock.retrieve_skill_catalog.return_value = returned_catalog
        self.memory_service_mock.retrieve_all_memories.return_value = []
        self.knowledge_service_mock.retrieve_knowledge.return_value = []

        # when
        actual_context = asyncio.run(self.data_orchestration_service.recall(input_context))

        # then
        assert actual_context == expected_context

        assert self.skill_service_mock.mock_calls == [
            call.retrieve_skills(""),
            call.retrieve_skill_catalog()
        ]
