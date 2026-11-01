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


async def test_should_return_tool_output_on_call_even_if_tool_reports_an_error(
        external_tool_service,
        mcp_broker,
        logging_broker,
        create_random_string,
        expected_arguments_json):

    # given
    random_name = create_random_string()
    random_input = create_random_string()
    tool_reported_error = "error: upstream returned no data"
    expected_output = tool_reported_error
    mcp_broker.call.return_value = tool_reported_error

    # when
    actual_output = await external_tool_service.call(random_name, random_input)

    # then
    assert actual_output == expected_output

    assert mcp_broker.mock_calls == [
        call.call(random_name, expected_arguments_json(random_input))]

    assert logging_broker.mock_calls == []


async def test_should_call_with_the_arguments_as_given_on_call_if_input_is_a_json_object(
        external_tool_service, mcp_broker, logging_broker, create_random_string):
    """A JSON object is handed to the server exactly as the model wrote it.

    Found in the 2026-09-04 principal review (F-03): every call was forced into one string
    argument named "input", so a tool with a typed, multi-property schema could never be called
    correctly. Plain text still travels as that one argument, as it is what the text protocol
    produces and what a schema-less tool understands, but a JSON object, which is what a native
    call produces, goes over as given.
    """
    # given
    input_name = create_random_string()
    random_output = create_random_string()
    structured_input = '{"city":"Seattle","days":3}'
    expected_output = random_output
    mcp_broker.call.return_value = random_output

    # when
    actual_output = await external_tool_service.call(input_name, structured_input)

    # then
    assert actual_output == expected_output
    assert mcp_broker.mock_calls == [call.call(input_name, structured_input)]
    assert logging_broker.mock_calls == []
