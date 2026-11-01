# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.foundations.knowledges.exceptions import (
    InvalidKnowledgeException,
    KnowledgeValidationException)
from tests.unit.services.foundations.knowledges.knowledge_service_tests import (
    KnowledgeServiceTests)


class TestKnowledgeServiceValidationsRetrieve(KnowledgeServiceTests):
    @pytest.mark.parametrize("invalid_query", [None, "", "   "])
    def test_should_raise_validation_exception_on_retrieve_if_query_is_invalid_and_log_it(
        self,
        invalid_query: str) -> None:

        # given
        invalid_knowledge_exception = InvalidKnowledgeException(
            message="Invalid knowledge. Please correct the errors and try again.")

        invalid_knowledge_exception.upsert_data_list("query", "Text is required")

        expected_knowledge_validation_exception = KnowledgeValidationException(
            message="Knowledge validation error occurred, fix the errors and try again.",
            inner_exception=invalid_knowledge_exception)

        # when
        with pytest.raises(KnowledgeValidationException) as actual_knowledge_validation_exception:
            asyncio.run(self.knowledge_service.retrieve_knowledge(invalid_query))

        # then
        assert expected_knowledge_validation_exception.same_exception_as(
            actual_knowledge_validation_exception.value)

        self.assert_logged_once("log_error", expected_knowledge_validation_exception)
        assert self.knowledge_broker_mock.mock_calls == []
