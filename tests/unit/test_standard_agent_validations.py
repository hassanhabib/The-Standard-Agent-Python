# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import uuid

import pytest

from standard_agents.models.clients.agents.exceptions import (
    InvalidAgentConfigurationException)
from standard_agents.standard_agent import StandardAgent


class TestStandardAgentValidations:
    def test_should_raise_configuration_exception_on_run_if_no_brain_is_configured(
        self) -> None:

        # given
        input_prompt = uuid.uuid4().hex
        agent = StandardAgent()

        expected_exception = InvalidAgentConfigurationException(
            message="Invalid agent configuration. Please correct the errors and try again.")

        expected_exception.upsert_data_list(
            "brain",
            "A brain is required: compose one with on_brain or use_generator")

        # when
        with pytest.raises(InvalidAgentConfigurationException) as actual_exception:
            asyncio.run(agent.run(input_prompt))

        # then
        assert expected_exception.same_exception_as(actual_exception.value)
