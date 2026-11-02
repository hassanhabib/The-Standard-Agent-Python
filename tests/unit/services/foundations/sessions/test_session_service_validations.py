# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.brokers.sessions.agent_session import AgentSession
from standard_agents.models.foundations.sessions.exceptions import (
    InvalidSessionException,
    SessionValidationException)


def _session_validation_exception() -> SessionValidationException:
    invalid_session_exception = InvalidSessionException(
        message="Invalid session. Please correct the error and try again.")

    return SessionValidationException(
        message="Session validation error occurred, fix the error and try again.",
        inner_exception=invalid_session_exception)


@pytest.mark.parametrize("invalid_session_id", [None, "", " "])
async def test_should_throw_validation_exception_on_retrieve_session_if_id_is_invalid_and_log_it(
        invalid_session_id, session_service, session_broker, logging_broker, same_exception_as):

    # given
    expected_session_validation_exception = _session_validation_exception()

    # when
    with pytest.raises(SessionValidationException) as raised:
        await session_service.retrieve_session(invalid_session_id)

    # then
    assert raised.value.same_exception_as(expected_session_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_session_validation_exception))]

    assert session_broker.mock_calls == []


@pytest.mark.parametrize("invalid_session_id", [None, "", " "])
async def test_should_throw_validation_exception_on_record_session_if_id_is_invalid_and_log_it(
        invalid_session_id, session_service, session_broker, logging_broker, same_exception_as):
    """A session written without an id cannot be read back.

    Nothing throws, the next prompt finds nothing, and the agent forgets, with no error anywhere
    to explain it.
    """
    # given
    invalid_session = AgentSession(id=invalid_session_id)
    expected_session_validation_exception = _session_validation_exception()

    # when
    with pytest.raises(SessionValidationException) as raised:
        await session_service.record_session(invalid_session)

    # then
    assert raised.value.same_exception_as(expected_session_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_session_validation_exception))]

    assert session_broker.mock_calls == []
