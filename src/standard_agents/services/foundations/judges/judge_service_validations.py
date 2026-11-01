# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.foundations.judges.exceptions import InvalidJudgeException


def validate_evaluate(task: str, candidate: str) -> None:
    validate(
        (is_invalid(task), "task"),
        (is_invalid(candidate), "candidate"))


def is_invalid(text: str) -> dict:
    return {
        "condition": text is None or text.strip() == "",
        "message": "Text is required"
    }


def validate(*validations: tuple[dict, str]) -> None:
    invalid_judge_exception = InvalidJudgeException(
        message="Invalid judge. Please correct the errors and try again.")

    for rule, parameter in validations:
        if rule["condition"]:
            invalid_judge_exception.upsert_data_list(parameter, rule["message"])

    invalid_judge_exception.throw_if_contains_errors()
