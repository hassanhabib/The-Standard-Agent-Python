# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.foundations.gates.exceptions import InvalidGateException


def validate_text(text: str) -> None:
    validate((is_invalid(text), "text"))


def is_invalid(text: str) -> dict:
    return {
        "condition": text is None or text.strip() == "",
        "message": "Text is required"
    }


def validate(*validations: tuple[dict, str]) -> None:
    invalid_gate_exception = InvalidGateException(
        message="Invalid gate. Please correct the errors and try again.")

    for rule, parameter in validations:
        if rule["condition"]:
            invalid_gate_exception.upsert_data_list(parameter, rule["message"])

    invalid_gate_exception.throw_if_contains_errors()
