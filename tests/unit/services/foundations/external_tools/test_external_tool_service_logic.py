# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call


async def test_should_call(
        external_tool_service,
        mcp_broker,
        logging_broker,
        create_random_string,
        expected_arguments_json):

    # given
    input_name = create_random_string()
    input_input = create_random_string()
    random_output = create_random_string()
    expected_output = random_output
    mcp_broker.call.return_value = random_output

    # when
    actual_output = await external_tool_service.call(input_name, input_input)

    # then
    assert actual_output == expected_output
    assert mcp_broker.mock_calls == [call.call(input_name, expected_arguments_json(input_input))]
    assert logging_broker.mock_calls == []
