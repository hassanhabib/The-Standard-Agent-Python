# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

import pytest

from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyException,
    FailedBrainDependencyException)
from tests.unit.services.foundations.brains.brain_service_tests import BrainServiceTests


class TestBrainServiceExceptionsGenerate(BrainServiceTests):
    def test_should_raise_critical_dependency_exception_on_generate_if_os_error_occurs_and_log_it(
        self) -> None:

        # given
        input_system_prompt = self.create_random_string()
        input_user_prompt = self.create_random_string()
        os_error = OSError(self.create_random_string())

        failed_brain_dependency_exception = FailedBrainDependencyException(
            message="Failed brain dependency error occurred, contact support.",
            inner_exception=os_error)

        expected_brain_dependency_exception = BrainDependencyException(
            message="Brain dependency error occurred, contact support.",
            inner_exception=failed_brain_dependency_exception)

        self.generator_broker_mock.generate.side_effect = os_error

        # when
        with pytest.raises(BrainDependencyException) as actual_brain_dependency_exception:
            asyncio.run(self.brain_service.generate(input_system_prompt, input_user_prompt))

        # then
        assert expected_brain_dependency_exception.same_exception_as(
            actual_brain_dependency_exception.value)

        assert self.generator_broker_mock.mock_calls == [
            call.generate(input_system_prompt, input_user_prompt)
        ]

        self.assert_logged_once("log_critical", expected_brain_dependency_exception)

    def test_should_raise_dependency_exception_on_generate_if_runtime_error_occurs_and_log_it(
        self) -> None:

        # given
        input_system_prompt = self.create_random_string()
        input_user_prompt = self.create_random_string()
        runtime_error = RuntimeError(self.create_random_string())

        failed_brain_dependency_exception = FailedBrainDependencyException(
            message="Failed brain dependency error occurred, contact support.",
            inner_exception=runtime_error)

        expected_brain_dependency_exception = BrainDependencyException(
            message="Brain dependency error occurred, contact support.",
            inner_exception=failed_brain_dependency_exception)

        self.generator_broker_mock.generate.side_effect = runtime_error

        # when
        with pytest.raises(BrainDependencyException) as actual_brain_dependency_exception:
            asyncio.run(self.brain_service.generate(input_system_prompt, input_user_prompt))

        # then
        assert expected_brain_dependency_exception.same_exception_as(
            actual_brain_dependency_exception.value)

        assert self.generator_broker_mock.mock_calls == [
            call.generate(input_system_prompt, input_user_prompt)
        ]

        self.assert_logged_once("log_error", expected_brain_dependency_exception)
