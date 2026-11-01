# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.foundations.external_tools.exceptions import (
    InvalidExternalToolException)


def validate_name(name: str) -> None:
    validate((is_invalid(name), "name"))


def is_invalid(text: str) -> dict:
    return {
        "condition": text is None or text.strip() == "",
        "message": "Text is required"
    }


def validate(*validations: tuple[dict, str]) -> None:
    invalid_external_tool_exception = InvalidExternalToolException(
        message="Invalid external tool. Please correct the errors and try again.")

    for rule, parameter in validations:
        if rule["condition"]:
            invalid_external_tool_exception.upsert_data_list(parameter, rule["message"])

    invalid_external_tool_exception.throw_if_contains_errors()
