# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import copy
from unittest.mock import call

from standard_agents.brokers.files.file_broker import SearchOption
from standard_agents.services.foundations.knowledges.knowledge_service import KnowledgeService


async def test_should_retrieve_knowledge(
        knowledge_service,
        knowledge_broker,
        logging_broker,
        create_random_string,
        create_random_documents):

    # given
    input_query = create_random_string()
    retrieved_documents = create_random_documents()
    knowledge_broker.select_knowledge.return_value = retrieved_documents
    expected_documents = list(retrieved_documents)

    # when
    actual_documents = await knowledge_service.retrieve_knowledge(input_query)

    # then
    assert list(actual_documents) == expected_documents
    assert knowledge_broker.mock_calls == [call.select_knowledge(input_query)]
    assert logging_broker.mock_calls == []


async def test_should_retrieve_no_knowledge_on_retrieve_knowledge_if_nothing_matches(
        knowledge_service, knowledge_broker, logging_broker, create_random_string):

    # given
    random_query = create_random_string()
    knowledge_broker.select_knowledge.return_value = []

    # when
    actual_documents = await knowledge_service.retrieve_knowledge(random_query)

    # then
    assert not actual_documents
    assert knowledge_broker.mock_calls == [call.select_knowledge(random_query)]
    assert logging_broker.mock_calls == []


async def test_should_return_empty_knowledge_if_knowledge_directory_does_not_exist(
        file_broker, logging_broker, create_random_string):

    # given
    knowledge_path = create_random_string()
    search_pattern = "*.md"
    max_results = 3
    query = create_random_string()

    file_knowledge_service = KnowledgeService(
        file_broker=file_broker,
        knowledge_path=knowledge_path,
        search_pattern=search_pattern,
        max_results=max_results,
        logging_broker=logging_broker)

    file_broker.directory_exists.return_value = False

    # when
    actual_documents = await file_knowledge_service.retrieve_knowledge(query)

    # then
    assert not actual_documents
    assert file_broker.mock_calls == [call.directory_exists(knowledge_path)]
    assert logging_broker.mock_calls == []


async def test_should_retrieve_the_most_relevant_knowledge_up_to_max_results(
        file_broker, logging_broker, create_random_string):
    """Every document is read, because relevance is relative (SPEC.md 4.2).

    A term's weight depends on how rare it is across the corpus, which is not knowable from a
    prefix of it. The old contract stopped reading once it had enough matches, and so could only
    ever return the first ones found.
    """
    # given
    knowledge_path = create_random_string()
    search_pattern = "*.md"
    max_results = 2
    query = "needle"

    first_path = "a.md"
    second_path = "b.md"
    third_path = "c.md"
    fourth_path = "d.md"
    unordered_paths = [third_path, first_path, fourth_path, second_path]

    first_document = "alpha needle"
    second_document = "beta"  # carries no query term, scores zero
    third_document = "gamma NEEDLE"  # case-insensitive
    fourth_document = "delta needle"

    documents_by_path = {
        first_path: first_document,
        second_path: second_document,
        third_path: third_document,
        fourth_path: fourth_document}

    file_knowledge_service = KnowledgeService(
        file_broker=file_broker,
        knowledge_path=knowledge_path,
        search_pattern=search_pattern,
        max_results=max_results,
        logging_broker=logging_broker)

    file_broker.directory_exists.return_value = True
    file_broker.select_files.return_value = unordered_paths
    file_broker.read_file.side_effect = lambda path: documents_by_path[path]

    # when
    actual_documents = await file_knowledge_service.retrieve_knowledge(query)

    # then: the best matches, capped, and never the document carrying no query term
    assert len(actual_documents) == max_results
    assert second_document not in actual_documents
    assert all("needle" in document.casefold() for document in actual_documents)

    assert file_broker.mock_calls == [
        call.directory_exists(knowledge_path),
        call.select_files(knowledge_path, search_pattern, SearchOption.ALL_DIRECTORIES),
        call.read_file(first_path),
        call.read_file(second_path),
        call.read_file(third_path),
        call.read_file(fourth_path)]

    assert logging_broker.mock_calls == []


async def test_should_retrieve_sourced_knowledge(
        sourced_knowledge_service,
        sourced_knowledge_broker,
        knowledge_broker,
        logging_broker,
        create_random_string,
        create_random_knowledge_results):

    # given
    input_query = create_random_string()
    selected_knowledge_results = create_random_knowledge_results()
    expected_knowledge_results = copy.deepcopy(selected_knowledge_results)
    sourced_knowledge_broker.select_sourced_knowledge.return_value = selected_knowledge_results

    # when
    actual_knowledge_results = await sourced_knowledge_service.retrieve_sourced_knowledge(
        input_query)

    # then
    assert list(actual_knowledge_results) == expected_knowledge_results

    assert sourced_knowledge_broker.mock_calls == [
        call.select_sourced_knowledge(input_query)]

    assert knowledge_broker.mock_calls == []
    assert logging_broker.mock_calls == []
