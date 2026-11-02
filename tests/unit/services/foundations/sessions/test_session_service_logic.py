# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call


async def test_should_retrieve_session(
        session_service,
        session_broker,
        logging_broker,
        create_random_string,
        create_random_session):

    # given
    random_session_id = create_random_string()
    random_session = create_random_session()
    retrieved_session = random_session
    expected_session = retrieved_session
    session_broker.select_session.return_value = retrieved_session

    # when
    actual_session = await session_service.retrieve_session(random_session_id)

    # then
    assert actual_session == expected_session
    assert session_broker.mock_calls == [call.select_session(random_session_id)]
    assert logging_broker.mock_calls == []


async def test_should_retrieve_no_session_on_retrieve_session_if_none_exists(
        session_service, session_broker, logging_broker, create_random_string):
    """A conversation that has not started yet is not an error.

    It is the ordinary first prompt, and the caller has to be able to tell it apart from a
    failure to read.
    """
    # given
    random_session_id = create_random_string()
    session_broker.select_session.return_value = None

    # when
    actual_session = await session_service.retrieve_session(random_session_id)

    # then
    assert actual_session is None
    assert session_broker.mock_calls == [call.select_session(random_session_id)]
    assert logging_broker.mock_calls == []


async def test_should_record_session(
        session_service, session_broker, logging_broker, create_random_session):

    # given
    random_session = create_random_session()
    input_session = random_session

    # when
    await session_service.record_session(input_session)

    # then
    assert session_broker.mock_calls == [call.upsert_session(input_session)]
    assert logging_broker.mock_calls == []
