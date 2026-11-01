# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

from tests.unit.services.foundations.memories.memory_service_tests import MemoryServiceTests


class TestMemoryServiceLogicRetrieveAll(MemoryServiceTests):
    def test_should_retrieve_all_memories_without_blank_lines(self) -> None:
        # given
        first_memory = self.create_random_string()
        second_memory = self.create_random_string()
        returned_memories = [first_memory, "", "   ", second_memory]
        expected_memories = [first_memory, second_memory]
        self.memory_broker_mock.select_all_memories.return_value = returned_memories

        # when
        actual_memories = asyncio.run(self.memory_service.retrieve_all_memories())

        # then
        assert actual_memories == expected_memories
        assert self.memory_broker_mock.mock_calls == [call.select_all_memories()]
        assert self.logging_broker_mock.mock_calls == []
