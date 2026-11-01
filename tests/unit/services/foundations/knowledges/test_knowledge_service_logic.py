# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

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
