# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.foundations.brains.exceptions import InvalidBrainException


def validate_user_prompt(user_prompt: str) -> None:
    validate((is_invalid(user_prompt), "user_prompt"))


def is_invalid(text: str) -> dict:
    return {
        "condition": text is None or text.strip() == "",
        "message": "Text is required"
    }


def validate(*validations: tuple[dict, str]) -> None:
    invalid_brain_exception = InvalidBrainException(
        message="Invalid brain. Please correct the errors and try again.")

    for rule, parameter in validations:
        if rule["condition"]:
            invalid_brain_exception.upsert_data_list(parameter, rule["message"])

    invalid_brain_exception.throw_if_contains_errors()
