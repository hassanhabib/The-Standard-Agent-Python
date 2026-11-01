# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from standard_agents.brokers.files.file_broker import FileBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.models.foundations.memories.exceptions import (
    FailedMemoryDependencyException,
    InvalidMemoryException,
    MemoryDependencyException,
    MemoryValidationException)


class MemoryService:
    """What the agent remembers across runs, kept by a memory broker or in a file of lines."""

    def __init__(
            self,
            *,
            logging_broker: LoggingBroker,
            memory_broker: MemoryBroker | None = None,
            file_broker: FileBroker | None = None,
            memory_path: str = "") -> None:

        self.memory_broker = memory_broker
        self.file_broker = file_broker
        self.memory_path = memory_path
        self.logging_broker = logging_broker

        # Appends are serialized: two callers remembering at once write to the file at the same
        # moment and one memory can be lost (principal review 2026-09-04, F-05). Per instance,
        # because the file is per instance; a store shared across processes is a memory
        # broker's job, not this file's.
        self._memory_file_lock = asyncio.Lock()

    async def recall_memories(self) -> Sequence[str]:
        async with _handling_exceptions(self.logging_broker):
            if self.file_broker is not None:
                return await self._select_memories_from_file(self.file_broker)

            return await self.memory_broker.select_memories()

    async def remember(self, memory: str) -> None:
        async with _handling_exceptions(self.logging_broker):
            _validate_memory(memory)

            if self.file_broker is not None:
                await self._insert_memory_into_file(self.file_broker, memory)
            else:
                await self.memory_broker.insert_memory(memory)

    async def _select_memories_from_file(self, file_broker: FileBroker) -> Sequence[str]:
        if not file_broker.file_exists(self.memory_path):
            return ()

        return await file_broker.read_all_lines(self.memory_path)

    async def _insert_memory_into_file(self, file_broker: FileBroker, memory: str) -> None:
        async with self._memory_file_lock:
            file_broker.create_directory(os.path.dirname(self.memory_path))
            await file_broker.append_all_lines(self.memory_path, (memory,))


def _validate_memory(memory: str | None) -> None:
    if not memory or memory.isspace():
        raise InvalidMemoryException(
            message="Invalid memory. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidMemoryException as invalid_memory_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_memory_exception)
    except (FileNotFoundError, NotADirectoryError, PermissionError) as critical_error:
        raise await _create_and_log_critical_dependency_exception(
            logging_broker, critical_error)
    except OSError as os_error:
        raise await _create_and_log_dependency_exception(logging_broker, os_error)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> MemoryValidationException:

    memory_validation_exception = MemoryValidationException(
        message="Memory validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(memory_validation_exception)

    return memory_validation_exception


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> MemoryDependencyException:

    memory_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_critical(memory_dependency_exception)

    return memory_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> MemoryDependencyException:

    memory_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(memory_dependency_exception)

    return memory_dependency_exception


def _create_dependency_exception(exception: Exception) -> MemoryDependencyException:
    failed_memory_dependency_exception = FailedMemoryDependencyException(
        message="Failed memory dependency error occurred, contact support.",
        inner_exception=exception)

    return MemoryDependencyException(
        message="Memory dependency error occurred, contact support.",
        inner_exception=failed_memory_dependency_exception)
