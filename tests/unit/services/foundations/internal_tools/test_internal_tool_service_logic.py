# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest


@pytest.mark.parametrize("broker_has_tool", [True, False])
async def test_should_handles(
        broker_has_tool, internal_tool_service, tool_broker, logging_broker, create_random_string):

    # given
    input_name = create_random_string()
    expected_outcome = broker_has_tool
    tool_broker.has.return_value = broker_has_tool

    # when
    actual_outcome = await internal_tool_service.handles(input_name)

    # then
    assert actual_outcome is expected_outcome
    assert tool_broker.mock_calls == [call.has(input_name)]
    assert logging_broker.mock_calls == []


async def test_should_run(
        internal_tool_service, tool_broker, logging_broker, create_random_string):

    # given
    input_name = create_random_string()
    input_input = create_random_string()
    random_output = create_random_string()
    expected_output = random_output
    tool_broker.run.return_value = random_output

    # when
    actual_output = await internal_tool_service.run(input_name, input_input)

    # then
    assert actual_output == expected_output
    assert tool_broker.mock_calls == [call.run(input_name, input_input)]
    assert logging_broker.mock_calls == []
