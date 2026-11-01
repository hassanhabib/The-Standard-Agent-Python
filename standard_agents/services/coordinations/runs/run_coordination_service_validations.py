# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.coordinations.runs.exceptions import InvalidRunException


def validate_prompt(prompt: str) -> None:
    validate((is_invalid(prompt), "prompt"))


def is_invalid(text: str) -> dict:
    return {
        "condition": text is None or text.strip() == "",
        "message": "Text is required"
    }


def validate(*validations: tuple[dict, str]) -> None:
    invalid_run_exception = InvalidRunException(
        message="Invalid run. Please correct the errors and try again.")

    for rule, parameter in validations:
        if rule["condition"]:
            invalid_run_exception.upsert_data_list(parameter, rule["message"])

    invalid_run_exception.throw_if_contains_errors()
