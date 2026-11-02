# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.memories.exceptions import (
    InvalidMemoryException,
    MemoryValidationException)


@pytest.mark.parametrize("invalid_memory", [None, "", " "])
async def test_should_throw_validation_exception_on_remember_if_memory_is_invalid_and_log_it(
        invalid_memory, memory_service, memory_broker, logging_broker, same_exception_as):

    # given
    invalid_memory_exception = InvalidMemoryException(
        message="Invalid memory. Please correct the error and try again.")

    expected_memory_validation_exception = MemoryValidationException(
        message="Memory validation error occurred, fix the error and try again.",
        inner_exception=invalid_memory_exception)

    # when
    with pytest.raises(MemoryValidationException) as raised:
        await memory_service.remember(invalid_memory)

    # then
    assert raised.value.same_exception_as(expected_memory_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_memory_validation_exception))]

    assert memory_broker.mock_calls == []
