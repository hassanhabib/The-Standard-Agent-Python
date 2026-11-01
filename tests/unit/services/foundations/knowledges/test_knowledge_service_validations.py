# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.knowledges.exceptions import (
    InvalidKnowledgeException,
    KnowledgeValidationException)


def _knowledge_validation_exception() -> KnowledgeValidationException:
    invalid_knowledge_exception = InvalidKnowledgeException(
        message="Invalid knowledge query. Please correct the error and try again.")

    return KnowledgeValidationException(
        message="Knowledge validation error occurred, fix the error and try again.",
        inner_exception=invalid_knowledge_exception)


@pytest.mark.parametrize("invalid_query", [None, "", " "])
async def test_should_throw_validation_exception_on_retrieve_knowledge_if_query_is_invalid_and_log_it(
        invalid_query, knowledge_service, knowledge_broker, logging_broker, same_exception_as):

    # given
    expected_knowledge_validation_exception = _knowledge_validation_exception()

    # when
    with pytest.raises(KnowledgeValidationException) as raised:
        await knowledge_service.retrieve_knowledge(invalid_query)

    # then
    assert raised.value.same_exception_as(expected_knowledge_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_knowledge_validation_exception))]

    assert knowledge_broker.mock_calls == []


@pytest.mark.parametrize("invalid_query", [None, "", " "])
async def test_should_throw_validation_exception_on_retrieve_sourced_knowledge_if_query_is_invalid_and_log_it(
        invalid_query,
        sourced_knowledge_service,
        sourced_knowledge_broker,
        knowledge_broker,
        logging_broker,
        same_exception_as):

    # given
    expected_knowledge_validation_exception = _knowledge_validation_exception()

    # when
    with pytest.raises(KnowledgeValidationException) as raised:
        await sourced_knowledge_service.retrieve_sourced_knowledge(invalid_query)

    # then
    assert raised.value.same_exception_as(expected_knowledge_validation_exception)

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_knowledge_validation_exception))]

    assert sourced_knowledge_broker.mock_calls == []
    assert knowledge_broker.mock_calls == []
