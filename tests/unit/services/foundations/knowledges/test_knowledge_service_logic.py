# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call


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
