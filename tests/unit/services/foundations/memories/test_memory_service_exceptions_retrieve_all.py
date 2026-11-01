# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.memories.exceptions import (
    FailedMemoryDependencyException,
    MemoryDependencyException)
from tests.unit.services.foundations.memories.memory_service_tests import MemoryServiceTests


class TestMemoryServiceExceptionsRetrieveAll(MemoryServiceTests):
    def test_should_raise_critical_dependency_exception_on_retrieve_all_if_os_error_occurs_and_log_it(
        self) -> None:

        # given
        os_error = OSError(self.create_random_string())

        failed_memory_dependency_exception = FailedMemoryDependencyException(
            message="Failed memory dependency error occurred, contact support.",
            inner_exception=os_error)

        expected_memory_dependency_exception = MemoryDependencyException(
            message="Memory dependency error occurred, contact support.",
            inner_exception=failed_memory_dependency_exception)

        self.memory_broker_mock.select_all_memories.side_effect = os_error

        # when
        with pytest.raises(MemoryDependencyException) as actual_memory_dependency_exception:
            asyncio.run(self.memory_service.retrieve_all_memories())

        # then
        assert expected_memory_dependency_exception.same_exception_as(
            actual_memory_dependency_exception.value)

        assert self.memory_broker_mock.mock_calls == [call.select_all_memories()]
        self.assert_logged_once("log_critical", expected_memory_dependency_exception)
