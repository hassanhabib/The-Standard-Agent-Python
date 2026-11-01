# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.foundations.judges.exceptions import (
    InvalidJudgeException,
    InvalidJudgementException)

MINIMUM_SCORE = 0.0
MAXIMUM_SCORE = 1.0


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


# A verdict is the dependency's answer, so a score out of range is the verifier's fault and is
# raised as an invalid judgement, apart from an invalid request.
def validate_score(score: float) -> None:
    invalid_judgement_exception = InvalidJudgementException(
        message="Invalid judgement. Please correct the errors and try again.")

    if score < MINIMUM_SCORE or score > MAXIMUM_SCORE:
        invalid_judgement_exception.upsert_data_list(
            "score",
            "Value must be between 0.0 and 1.0")

    invalid_judgement_exception.throw_if_contains_errors()
