# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The whole point of the foundation.

A store failure has to arrive as a SESSION failure: an OSError surfacing unmapped is what let a
full disk get blamed on the loop.
"""

from unittest.mock import call

import pytest

from standard_agents.brokers.sessions.db_concurrency_exception import DBConcurrencyException
from standard_agents.models.foundations.sessions.exceptions import (
    SessionDependencyValidationException,
    StaleSessionException)


async def test_should_throw_dependency_validation_exception_on_record_session_if_session_is_stale_and_log_it(
        session_service,
        session_broker,
        logging_broker,
        same_exception_as,
        create_random_session):
    """A store that refuses a write based on a stale read is the caller's to retry.

    Found in the 2026-09-04 principal review (F-06): it is not an outage. The native concurrency
    signal is localized into a session failure and categorized as dependency validation, so the
    tier above can tell "try again" from "the disk is gone".
    """
    # given
    random_session = create_random_session()
    db_concurrency_exception = DBConcurrencyException("the session moved on")

    stale_session_exception = StaleSessionException(
        message="The session was written by another prompt since it was read; "
            "read it again and retry.",
        inner_exception=db_concurrency_exception)

    expected_session_dependency_validation_exception = SessionDependencyValidationException(
        message="Session dependency validation error occurred, fix the error and try again.",
        inner_exception=stale_session_exception)

    session_broker.upsert_session.side_effect = db_concurrency_exception

    # when
    with pytest.raises(SessionDependencyValidationException) as raised:
        await session_service.record_session(random_session)

    # then
    assert raised.value.same_exception_as(expected_session_dependency_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_session_dependency_validation_exception))]

    assert session_broker.mock_calls == [call.upsert_session(random_session)]
