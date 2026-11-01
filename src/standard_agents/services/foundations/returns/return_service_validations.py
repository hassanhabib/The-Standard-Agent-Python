# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.foundations.returns.exceptions import InvalidReturnException


def validate_payload(payload: str) -> None:
    validate((is_invalid(payload), "payload"))


def is_invalid(text: str) -> dict:
    return {
        "condition": text is None or text.strip() == "",
        "message": "Text is required"
    }


def validate(*validations: tuple[dict, str]) -> None:
    invalid_return_exception = InvalidReturnException(
        message="Invalid return. Please correct the errors and try again.")

    for rule, parameter in validations:
        if rule["condition"]:
            invalid_return_exception.upsert_data_list(parameter, rule["message"])

    invalid_return_exception.throw_if_contains_errors()
