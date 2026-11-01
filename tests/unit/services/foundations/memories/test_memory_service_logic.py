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


async def test_should_remember_by_appending_to_memory_file(
        file_broker, logging_broker, create_random_string):

    # given
    memory_directory = create_random_string()
    memory_path = os.path.join(memory_directory, create_random_string() + ".txt")
    input_memory = create_random_string()
    file_memory_service = MemoryService(
        file_broker=file_broker, memory_path=memory_path, logging_broker=logging_broker)

    # when
    await file_memory_service.remember(input_memory)

    # then
    assert file_broker.mock_calls == [
        call.create_directory(memory_directory),
        call.append_all_lines(memory_path, (input_memory,))]

    assert logging_broker.mock_calls == []


async def test_should_remember_concurrently_to_file_without_losing_a_memory(
        tmp_path, logging_broker):
    """Every fact stored at once is in the file afterwards, whole and once.

    Found in the 2026-09-04 principal review (F-05): the file append was not serialized, so
    simultaneous remembers, the shape a hosted singleton meets when several callers store a fact
    at once, could collide on the file and fail, or interleave.
    """
    # given
    memory_path = str(tmp_path / "memory.txt")
    file_memory_service = MemoryService(
        file_broker=LocalFileBroker(), memory_path=memory_path, logging_broker=logging_broker)

    memories = [f"fact number {index}" for index in range(32)]

    # when
    await asyncio.gather(*(file_memory_service.remember(memory) for memory in memories))

    # then
    remembered_memories = (tmp_path / "memory.txt").read_text(encoding="utf-8").splitlines()
    assert sorted(remembered_memories) == sorted(memories)
    assert logging_broker.mock_calls == []
