# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.foundations.brains.exceptions import (
    BrainValidationException,
    InvalidBrainException)
from tests.unit.services.foundations.brains.brain_service_tests import BrainServiceTests


class TestBrainServiceValidationsGenerate(BrainServiceTests):
    @pytest.mark.parametrize("invalid_user_prompt", [None, "", "   "])
    def test_should_raise_validation_exception_on_generate_if_user_prompt_is_invalid_and_log_it(
        self,
        invalid_user_prompt: str) -> None:

        # given
        input_system_prompt = self.create_random_string()

        invalid_brain_exception = InvalidBrainException(
            message="Invalid brain. Please correct the errors and try again.")

        invalid_brain_exception.upsert_data_list("user_prompt", "Text is required")

        expected_brain_validation_exception = BrainValidationException(
            message="Brain validation error occurred, fix the errors and try again.",
            inner_exception=invalid_brain_exception)

        # when
        with pytest.raises(BrainValidationException) as actual_brain_validation_exception:
            asyncio.run(self.brain_service.generate(input_system_prompt, invalid_user_prompt))

        # then
        assert expected_brain_validation_exception.same_exception_as(
            actual_brain_validation_exception.value)

        self.assert_logged_once("log_error", expected_brain_validation_exception)
        assert self.generator_broker_mock.mock_calls == []
