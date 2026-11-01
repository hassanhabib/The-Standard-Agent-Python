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
