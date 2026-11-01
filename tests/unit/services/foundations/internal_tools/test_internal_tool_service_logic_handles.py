# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from tests.unit.services.foundations.internal_tools.internal_tool_service_tests import (
    InternalToolServiceTests)


class TestInternalToolServiceLogicHandles(InternalToolServiceTests):
    @pytest.mark.parametrize("returned_handles", [True, False])
    def test_should_tell_whether_it_handles_a_tool(self, returned_handles: bool) -> None:
        # given
        input_name = self.create_random_string()
        expected_handles = returned_handles
        self.tool_broker_mock.has.return_value = returned_handles

        # when
        actual_handles = asyncio.run(self.internal_tool_service.handles(input_name))

        # then
        assert actual_handles == expected_handles
        assert self.tool_broker_mock.mock_calls == [call.has(input_name)]
        assert self.logging_broker_mock.mock_calls == []
