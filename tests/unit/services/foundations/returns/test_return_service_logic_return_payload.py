# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

from tests.unit.services.foundations.returns.return_service_tests import ReturnServiceTests


class TestReturnServiceLogicReturnPayload(ReturnServiceTests):
    def test_should_return_payload(self) -> None:
        # given
        input_payload = self.create_random_string()
        expected_payload = input_payload

        # when
        actual_payload = asyncio.run(self.return_service.return_payload(input_payload))

        # then
        assert actual_payload == expected_payload
        assert self.logging_broker_mock.mock_calls == []
