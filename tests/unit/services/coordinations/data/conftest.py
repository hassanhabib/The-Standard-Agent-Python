# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import random
import uuid
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.coordinations.data.data_coordination_service import (
    DataCoordinationService)
from standard_agents.services.foundations.external_tools.external_tool_service import (
    ExternalToolService)
from standard_agents.services.foundations.knowledges.knowledge_service import KnowledgeService
from standard_agents.services.foundations.memories.memory_service import MemoryService
from standard_agents.services.foundations.sessions.session_service import SessionService
from standard_agents.services.foundations.skills.skill_service import SkillService
from standard_agents.services.orchestrations.data.recollections.recollection_orchestration_service \
    import RecollectionOrchestrationService
from standard_agents.services.orchestrations.data.retrievals.retrieval_orchestration_service \
    import RetrievalOrchestrationService
from xeptions import Xeption

TOOL_CATALOG = "- calculator — Evaluate arithmetic. parameters: {}"


class SameExceptionAs:
    """Matches, in a recorded call, an exception equivalent to the expected one."""

    def __init__(self, expected_exception: Xeption) -> None:
        self.expected_exception = expected_exception

    def __eq__(self, actual_exception: object) -> bool:
        return self.expected_exception.same_exception_as(actual_exception)

    def __repr__(self) -> str:
        return f"SameExceptionAs({self.expected_exception!r})"


@pytest.fixture
def skill_service() -> SkillService:
    return create_autospec(SkillService, instance=True)


@pytest.fixture
def memory_service() -> MemoryService:
    return create_autospec(MemoryService, instance=True)


@pytest.fixture
def knowledge_service() -> KnowledgeService:
    knowledge_service = create_autospec(KnowledgeService, instance=True)
    knowledge_service.retrieve_sourced_knowledge.return_value = []

    return knowledge_service


@pytest.fixture
def external_tool_service() -> ExternalToolService:
    # No remote servers in these tests: the foundation answers with an empty catalog, the same
    # answer the not-configured broker gives a real composition.
    external_tool_service = create_autospec(ExternalToolService, instance=True)
    external_tool_service.retrieve_tools.return_value = []

    return external_tool_service


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def data_coordination_service(
        skill_service,
        memory_service,
        knowledge_service,
        external_tool_service,
        logging_broker) -> DataCoordinationService:
    """The regions are real; the mocks stay at the foundation level."""
    return DataCoordinationService(
        retrieval_service=RetrievalOrchestrationService(
            skill_service=skill_service,
            knowledge_service=knowledge_service,
            tool_catalog=TOOL_CATALOG,
            logging_broker=logging_broker,
            external_tool_service=external_tool_service),
        recollection_service=RecollectionOrchestrationService(
            memory_service=memory_service,
            session_service=create_autospec(SessionService, instance=True),
            logging_broker=logging_broker),
        logging_broker=logging_broker)


@pytest.fixture
def tool_catalog() -> str:
    return TOOL_CATALOG


@pytest.fixture
def same_exception_as():
    return SameExceptionAs


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def create_random_knowledge_result(create_random_string):
    return lambda source: KnowledgeResult(
        text=create_random_string(),
        score=random.uniform(0.1, 10.0),
        source=source)


@pytest.fixture
def create_random_agent_context(create_random_string):
    return lambda: AgentContext(prompt=create_random_string())
