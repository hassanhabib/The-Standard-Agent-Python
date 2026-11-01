# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.knowledges.exceptions import (
    FailedKnowledgeDependencyException,
    KnowledgeDependencyException)

_CRITICAL_DEPENDENCY_EXCEPTIONS = pytest.mark.parametrize(
    "critical_dependency_exception",
    [FileNotFoundError(), NotADirectoryError(), PermissionError()],
    ids=["file-not-found", "directory-not-found", "unauthorized-access"])


def _knowledge_dependency_exception(inner_exception: Exception) -> KnowledgeDependencyException:
    failed_knowledge_dependency_exception = FailedKnowledgeDependencyException(
        message="Failed knowledge dependency error occurred, contact support.",
        inner_exception=inner_exception)

    return KnowledgeDependencyException(
        message="Knowledge dependency error occurred, contact support.",
        inner_exception=failed_knowledge_dependency_exception)


@_CRITICAL_DEPENDENCY_EXCEPTIONS
async def test_should_throw_dependency_exception_on_retrieve_knowledge_if_critical_error_occurs_and_log_it(
        critical_dependency_exception,
        knowledge_service,
        knowledge_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_query = create_random_string()

    expected_knowledge_dependency_exception = _knowledge_dependency_exception(
        critical_dependency_exception)

    knowledge_broker.select_knowledge.side_effect = critical_dependency_exception

    # when
    with pytest.raises(KnowledgeDependencyException) as raised:
        await knowledge_service.retrieve_knowledge(random_query)

    # then
    assert raised.value.same_exception_as(expected_knowledge_dependency_exception)
    assert knowledge_broker.mock_calls == [call.select_knowledge(random_query)]

    assert logging_broker.mock_calls == [
        call.log_critical(same_exception_as(expected_knowledge_dependency_exception))]
