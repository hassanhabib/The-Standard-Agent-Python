# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import random
import uuid
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.files.file_broker import FileBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.knowledges.sourced_knowledge_broker import SourcedKnowledgeBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.services.foundations.knowledges.knowledge_service import KnowledgeService
from xeptions import Xeption


class SameExceptionAs:
    """Matches, in a recorded call, an exception equivalent to the expected one."""

    def __init__(self, expected_exception: Xeption) -> None:
        self.expected_exception = expected_exception

    def __eq__(self, actual_exception: object) -> bool:
        return self.expected_exception.same_exception_as(actual_exception)

    def __repr__(self) -> str:
        return f"SameExceptionAs({self.expected_exception!r})"


@pytest.fixture
def knowledge_broker() -> KnowledgeBroker:
    return create_autospec(KnowledgeBroker, instance=True)


@pytest.fixture
def sourced_knowledge_broker() -> SourcedKnowledgeBroker:
    return create_autospec(SourcedKnowledgeBroker, instance=True)


@pytest.fixture
def file_broker() -> FileBroker:
    return create_autospec(FileBroker, instance=True)


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def knowledge_service(knowledge_broker, logging_broker) -> KnowledgeService:
    return KnowledgeService(knowledge_broker=knowledge_broker, logging_broker=logging_broker)


@pytest.fixture
def sourced_knowledge_service(sourced_knowledge_broker, logging_broker) -> KnowledgeService:
    return KnowledgeService(
        sourced_knowledge_broker=sourced_knowledge_broker, logging_broker=logging_broker)


@pytest.fixture
def same_exception_as():
    return SameExceptionAs


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def create_random_documents(create_random_string):
    return lambda: [create_random_string() for _ in range(3)]


@pytest.fixture
def create_random_knowledge_results(create_random_string):
    return lambda: [
        KnowledgeResult(
            text=create_random_string(),
            score=random.uniform(0.1, 10.0),
            source=create_random_string())
        for _ in range(3)]
