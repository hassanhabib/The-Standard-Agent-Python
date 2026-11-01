# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.foundations.knowledges.exceptions import InvalidKnowledgeException


def validate_query(query: str) -> None:
    validate((is_invalid(query), "query"))


def is_invalid(text: str) -> dict:
    return {
        "condition": text is None or text.strip() == "",
        "message": "Text is required"
    }


def validate(*validations: tuple[dict, str]) -> None:
    invalid_knowledge_exception = InvalidKnowledgeException(
        message="Invalid knowledge. Please correct the errors and try again.")

    for rule, parameter in validations:
        if rule["condition"]:
            invalid_knowledge_exception.upsert_data_list(parameter, rule["message"])

    invalid_knowledge_exception.throw_if_contains_errors()
