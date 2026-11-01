# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.models.clients.agents.exceptions import (
    InvalidAgentConfigurationException)


def validate_brain(generator_broker: IGeneratorBroker | None) -> None:
    validate((
        {
            "condition": generator_broker is None,
            "message": "A brain is required: compose one with on_brain or use_generator"
        },
        "brain"))


def validate_turns(turns: int) -> None:
    validate((
        {
            "condition": turns < 1,
            "message": "Value must be at least 1"
        },
        "max_turns"))


def validate(*validations: tuple[dict, str]) -> None:
    invalid_agent_configuration_exception = InvalidAgentConfigurationException(
        message="Invalid agent configuration. Please correct the errors and try again.")

    for rule, parameter in validations:
        if rule["condition"]:
            invalid_agent_configuration_exception.upsert_data_list(parameter, rule["message"])

    invalid_agent_configuration_exception.throw_if_contains_errors()
