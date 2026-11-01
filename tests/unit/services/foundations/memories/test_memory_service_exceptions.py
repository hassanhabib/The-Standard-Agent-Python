# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.memories.exceptions import (
    FailedMemoryDependencyException,
    FailedMemoryServiceException,
    MemoryDependencyException,
    MemoryServiceException)


def _memory_dependency_exception(inner_exception: Exception) -> MemoryDependencyException:
    failed_memory_dependency_exception = FailedMemoryDependencyException(
        message="Failed memory dependency error occurred, contact support.",
        inner_exception=inner_exception)

    return MemoryDependencyException(
        message="Memory dependency error occurred, contact support.",
        inner_exception=failed_memory_dependency_exception)


@pytest.mark.parametrize(
    "critical_dependency_exception",
    [FileNotFoundError(), NotADirectoryError(), PermissionError()],
    ids=["file-not-found", "directory-not-found", "unauthorized-access"])
async def test_should_throw_dependency_exception_on_recall_memories_if_critical_error_occurs_and_log_it(
        critical_dependency_exception,
        memory_service,
        memory_broker,
        logging_broker,
        same_exception_as):

    # given
    expected_memory_dependency_exception = _memory_dependency_exception(
        critical_dependency_exception)

    memory_broker.select_memories.side_effect = critical_dependency_exception

    # when
    with pytest.raises(MemoryDependencyException) as raised:
        await memory_service.recall_memories()

    # then
    assert raised.value.same_exception_as(expected_memory_dependency_exception)
    assert memory_broker.mock_calls == [call.select_memories()]

    assert logging_broker.mock_calls == [
        call.log_critical(same_exception_as(expected_memory_dependency_exception))]


async def test_should_throw_dependency_exception_on_recall_memories_if_io_error_occurs_and_log_it(
        memory_service, memory_broker, logging_broker, same_exception_as):

    # given
    io_error = OSError()
    expected_memory_dependency_exception = _memory_dependency_exception(io_error)
    memory_broker.select_memories.side_effect = io_error

    # when
    with pytest.raises(MemoryDependencyException) as raised:
        await memory_service.recall_memories()

    # then
    assert raised.value.same_exception_as(expected_memory_dependency_exception)
    assert memory_broker.mock_calls == [call.select_memories()]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_memory_dependency_exception))]


async def test_should_throw_service_exception_on_recall_memories_if_service_error_occurs_and_log_it(
        memory_service, memory_broker, logging_broker, same_exception_as):

    # given
    service_error = Exception()

    failed_memory_service_exception = FailedMemoryServiceException(
        message="Failed memory service error occurred, contact support.",
        inner_exception=service_error)

    expected_memory_service_exception = MemoryServiceException(
        message="Memory service error occurred, contact support.",
        inner_exception=failed_memory_service_exception)

    memory_broker.select_memories.side_effect = service_error

    # when
    with pytest.raises(MemoryServiceException) as raised:
        await memory_service.recall_memories()

    # then
    assert raised.value.same_exception_as(expected_memory_service_exception)
    assert memory_broker.mock_calls == [call.select_memories()]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_memory_service_exception))]


async def test_should_throw_dependency_exception_on_remember_if_dependency_error_occurs_and_log_it(
        memory_service, memory_broker, logging_broker, same_exception_as, create_random_string):

    # given
    random_memory = create_random_string()
    io_error = OSError()
    expected_memory_dependency_exception = _memory_dependency_exception(io_error)
    memory_broker.insert_memory.side_effect = io_error

    # when
    with pytest.raises(MemoryDependencyException) as raised:
        await memory_service.remember(random_memory)

    # then
    assert raised.value.same_exception_as(expected_memory_dependency_exception)
    assert memory_broker.mock_calls == [call.insert_memory(random_memory)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_memory_dependency_exception))]
