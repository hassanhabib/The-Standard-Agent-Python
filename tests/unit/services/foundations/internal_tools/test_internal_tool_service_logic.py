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
