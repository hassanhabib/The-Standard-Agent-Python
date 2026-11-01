# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import os
from unittest.mock import call

from standard_agents.brokers.files.local_file_broker import LocalFileBroker
from standard_agents.services.foundations.memories.memory_service import MemoryService


async def test_should_recall_memories(
        memory_service, memory_broker, logging_broker, create_random_memories):

    # given
    stored_memories = create_random_memories()
    memory_broker.select_memories.return_value = stored_memories
    expected_memories = list(stored_memories)

    # when
    actual_memories = await memory_service.recall_memories()

    # then
    assert list(actual_memories) == expected_memories
    assert memory_broker.mock_calls == [call.select_memories()]
    assert logging_broker.mock_calls == []
