# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

from tests.unit.services.foundations.external_tools.external_tool_service_tests import (
    ExternalToolServiceTests)


class TestExternalToolServiceLogicCall(ExternalToolServiceTests):
    def test_should_call_external_tool(self) -> None:
        # given
        input_name = self.create_random_string()
        input_payload = self.create_random_string()
        returned_outcome = self.create_random_string()
        expected_outcome = returned_outcome
        self.mcp_broker_mock.call.return_value = returned_outcome

        # when
        actual_outcome = asyncio.run(
            self.external_tool_service.call(input_name, input_payload))

        # then
        assert actual_outcome == expected_outcome
        assert self.mcp_broker_mock.mock_calls == [call.call(input_name, input_payload)]
        assert self.logging_broker_mock.mock_calls == []
