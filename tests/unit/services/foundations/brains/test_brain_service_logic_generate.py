# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

from tests.unit.services.foundations.brains.brain_service_tests import BrainServiceTests


class TestBrainServiceLogicGenerate(BrainServiceTests):
    def test_should_generate(self) -> None:
        # given
        input_system_prompt = self.create_random_string()
        input_user_prompt = self.create_random_string()
        random_reply = self.create_random_string()
        returned_reply = random_reply
        expected_reply = returned_reply
        self.generator_broker_mock.generate.return_value = returned_reply

        # when
        actual_reply = asyncio.run(
            self.brain_service.generate(input_system_prompt, input_user_prompt))

        # then
        assert actual_reply == expected_reply

        assert self.generator_broker_mock.mock_calls == [
            call.generate(input_system_prompt, input_user_prompt)
        ]

        assert self.logging_broker_mock.mock_calls == []
