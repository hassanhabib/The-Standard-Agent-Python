# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

from tests.unit.services.foundations.gates.gate_service_tests import GateServiceTests


class TestGateServiceLogicScreen(GateServiceTests):
    def test_should_screen_and_return_trimmed_verdict(self) -> None:
        # given
        input_text = self.create_random_string()
        random_verdict = self.create_random_string()
        returned_verdict = "  " + random_verdict + "\n"
        expected_verdict = random_verdict
        self.classifier_broker_mock.classify.return_value = returned_verdict

        # when
        actual_verdict = asyncio.run(self.gate_service.screen(input_text))

        # then
        assert actual_verdict == expected_verdict
        assert self.classifier_broker_mock.mock_calls == [call.classify(input_text)]
        assert self.logging_broker_mock.mock_calls == []
