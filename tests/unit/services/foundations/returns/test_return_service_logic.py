# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------


async def test_should_return(return_service, logging_broker, create_random_string):
    # given
    random_payload = create_random_string()
    input_payload = random_payload
    expected_payload = input_payload

    # when
    actual_payload = await return_service.return_payload(input_payload)

    # then
    assert actual_payload == expected_payload
    assert logging_broker.mock_calls == []
