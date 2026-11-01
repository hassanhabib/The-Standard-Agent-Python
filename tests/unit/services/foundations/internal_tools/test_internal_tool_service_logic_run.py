# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

from tests.unit.services.foundations.internal_tools.internal_tool_service_tests import (
    InternalToolServiceTests)


class TestInternalToolServiceLogicRun(InternalToolServiceTests):
    def test_should_run_tool(self) -> None:
        # given
        input_name = self.create_random_string()
        input_payload = self.create_random_string()
        returned_outcome = self.create_random_string()
        expected_outcome = returned_outcome
        self.tool_broker_mock.run.return_value = returned_outcome

        # when
        actual_outcome = asyncio.run(self.internal_tool_service.run(input_name, input_payload))

        # then
        assert actual_outcome == expected_outcome
        assert self.tool_broker_mock.mock_calls == [call.run(input_name, input_payload)]
        assert self.logging_broker_mock.mock_calls == []
