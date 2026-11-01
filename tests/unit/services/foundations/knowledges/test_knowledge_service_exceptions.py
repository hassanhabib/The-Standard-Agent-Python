# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.foundations.knowledges.exceptions import (
    FailedKnowledgeDependencyException,
    FailedKnowledgeServiceException,
    KnowledgeDependencyException,
    KnowledgeServiceException)

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


def _knowledge_service_exception(inner_exception: Exception) -> KnowledgeServiceException:
    failed_knowledge_service_exception = FailedKnowledgeServiceException(
        message="Failed knowledge service error occurred, contact support.",
        inner_exception=inner_exception)

    return KnowledgeServiceException(
        message="Knowledge service error occurred, contact support.",
        inner_exception=failed_knowledge_service_exception)


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


async def test_should_throw_dependency_exception_on_retrieve_knowledge_if_io_error_occurs_and_log_it(
        knowledge_service,
        knowledge_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_query = create_random_string()
    io_error = OSError()
    expected_knowledge_dependency_exception = _knowledge_dependency_exception(io_error)
    knowledge_broker.select_knowledge.side_effect = io_error

    # when
    with pytest.raises(KnowledgeDependencyException) as raised:
        await knowledge_service.retrieve_knowledge(random_query)

    # then
    assert raised.value.same_exception_as(expected_knowledge_dependency_exception)
    assert knowledge_broker.mock_calls == [call.select_knowledge(random_query)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_knowledge_dependency_exception))]


async def test_should_throw_service_exception_on_retrieve_knowledge_if_service_error_occurs_and_log_it(
        knowledge_service,
        knowledge_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_query = create_random_string()
    service_error = Exception()
    expected_knowledge_service_exception = _knowledge_service_exception(service_error)
    knowledge_broker.select_knowledge.side_effect = service_error

    # when
    with pytest.raises(KnowledgeServiceException) as raised:
        await knowledge_service.retrieve_knowledge(random_query)

    # then
    assert raised.value.same_exception_as(expected_knowledge_service_exception)
    assert knowledge_broker.mock_calls == [call.select_knowledge(random_query)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_knowledge_service_exception))]


@_CRITICAL_DEPENDENCY_EXCEPTIONS
async def test_should_throw_dependency_exception_on_retrieve_sourced_knowledge_if_critical_error_occurs_and_log_it(
        critical_dependency_exception,
        sourced_knowledge_service,
        sourced_knowledge_broker,
        knowledge_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_query = create_random_string()

    expected_knowledge_dependency_exception = _knowledge_dependency_exception(
        critical_dependency_exception)

    sourced_knowledge_broker.select_sourced_knowledge.side_effect = (
        critical_dependency_exception)

    # when
    with pytest.raises(KnowledgeDependencyException) as raised:
        await sourced_knowledge_service.retrieve_sourced_knowledge(random_query)

    # then
    assert raised.value.same_exception_as(expected_knowledge_dependency_exception)

    assert sourced_knowledge_broker.mock_calls == [
        call.select_sourced_knowledge(random_query)]

    assert logging_broker.mock_calls == [
        call.log_critical(same_exception_as(expected_knowledge_dependency_exception))]

    assert knowledge_broker.mock_calls == []


async def test_should_throw_dependency_exception_on_retrieve_sourced_knowledge_if_io_error_occurs_and_log_it(
        sourced_knowledge_service,
        sourced_knowledge_broker,
        knowledge_broker,
        logging_broker,
        same_exception_as,
        create_random_string):

    # given
    random_query = create_random_string()
    io_error = OSError()
    expected_knowledge_dependency_exception = _knowledge_dependency_exception(io_error)
    sourced_knowledge_broker.select_sourced_knowledge.side_effect = io_error

    # when
    with pytest.raises(KnowledgeDependencyException) as raised:
        await sourced_knowledge_service.retrieve_sourced_knowledge(random_query)

    # then
    assert raised.value.same_exception_as(expected_knowledge_dependency_exception)

    assert sourced_knowledge_broker.mock_calls == [
        call.select_sourced_knowledge(random_query)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_knowledge_dependency_exception))]

    assert knowledge_broker.mock_calls == []
