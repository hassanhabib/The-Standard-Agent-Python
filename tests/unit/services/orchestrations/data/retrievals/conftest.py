# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.services.foundations.external_tools.external_tool_service import (
    ExternalToolService)
from standard_agents.services.foundations.knowledges.knowledge_service import KnowledgeService
from standard_agents.services.foundations.skills.skill_service import SkillService
from standard_agents.services.orchestrations.data.retrievals.retrieval_orchestration_service \
    import RetrievalOrchestrationService

LOCAL_TOOL_CATALOG = "- calculator \u2014 Evaluates arithmetic. parameters: {}"


@pytest.fixture
def skill_service() -> SkillService:
    return create_autospec(SkillService, instance=True)


@pytest.fixture
def knowledge_service() -> KnowledgeService:
    return create_autospec(KnowledgeService, instance=True)


@pytest.fixture
def external_tool_service() -> ExternalToolService:
    return create_autospec(ExternalToolService, instance=True)


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def retrieval_orchestration_service(
        skill_service,
        knowledge_service,
        external_tool_service,
        logging_broker) -> RetrievalOrchestrationService:

    return RetrievalOrchestrationService(
        skill_service=skill_service,
        knowledge_service=knowledge_service,
        tool_catalog=LOCAL_TOOL_CATALOG,
        logging_broker=logging_broker,
        external_tool_service=external_tool_service)


@pytest.fixture
def local_tool_catalog() -> str:
    return LOCAL_TOOL_CATALOG


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex
