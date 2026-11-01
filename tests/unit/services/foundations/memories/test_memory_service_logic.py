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


async def test_should_recall_no_memories_on_recall_memories_if_store_is_empty(
        memory_service, memory_broker, logging_broker):

    # given
    memory_broker.select_memories.return_value = []

    # when
    actual_memories = await memory_service.recall_memories()

    # then
    assert not actual_memories
    assert memory_broker.mock_calls == [call.select_memories()]
    assert logging_broker.mock_calls == []


async def test_should_return_empty_memories_if_memory_file_does_not_exist(
        file_broker, logging_broker, create_random_string):

    # given
    memory_path = create_random_string()
    file_memory_service = MemoryService(
        file_broker=file_broker, memory_path=memory_path, logging_broker=logging_broker)

    file_broker.file_exists.return_value = False

    # when
    actual_memories = await file_memory_service.recall_memories()

    # then
    assert not actual_memories
    assert file_broker.mock_calls == [call.file_exists(memory_path)]
    assert logging_broker.mock_calls == []


async def test_should_recall_memories_from_file(
        file_broker, logging_broker, create_random_string, create_random_memories):

    # given
    memory_path = create_random_string()
    stored_memories = create_random_memories()
    expected_memories = list(stored_memories)
    file_memory_service = MemoryService(
        file_broker=file_broker, memory_path=memory_path, logging_broker=logging_broker)

    file_broker.file_exists.return_value = True
    file_broker.read_all_lines.return_value = stored_memories

    # when
    actual_memories = await file_memory_service.recall_memories()

    # then
    assert list(actual_memories) == expected_memories

    assert file_broker.mock_calls == [
        call.file_exists(memory_path),
        call.read_all_lines(memory_path)]

    assert logging_broker.mock_calls == []


async def test_should_remember(
        memory_service, memory_broker, logging_broker, create_random_string):

    # given
    input_memory = create_random_string()

    # when
    await memory_service.remember(input_memory)

    # then
    assert memory_broker.mock_calls == [call.insert_memory(input_memory)]
    assert logging_broker.mock_calls == []
