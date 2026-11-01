# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
from unittest.mock import call

from tests.unit.services.foundations.knowledges.knowledge_service_tests import (
    KnowledgeServiceTests)


class TestKnowledgeServiceLogicRetrieve(KnowledgeServiceTests):
    def test_should_retrieve_knowledge(self) -> None:
        # given
        input_query = self.create_random_string()
        returned_knowledge = [self.create_random_string(), self.create_random_string()]
        expected_knowledge = list(returned_knowledge)
        self.knowledge_broker_mock.select_knowledge.return_value = returned_knowledge

        # when
        actual_knowledge = asyncio.run(self.knowledge_service.retrieve_knowledge(input_query))

        # then
        assert actual_knowledge == expected_knowledge
        assert self.knowledge_broker_mock.mock_calls == [call.select_knowledge(input_query)]
        assert self.logging_broker_mock.mock_calls == []
