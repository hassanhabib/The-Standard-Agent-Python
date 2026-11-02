# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.sessions.session_broker import SessionBroker
from standard_agents.models.brokers.sessions.agent_session import AgentSession, AgentTurn
from standard_agents.services.foundations.sessions.session_service import SessionService
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
def session_broker() -> SessionBroker:
    return create_autospec(SessionBroker, instance=True)


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def session_service(session_broker, logging_broker) -> SessionService:
    return SessionService(session_broker=session_broker, logging_broker=logging_broker)


@pytest.fixture
def same_exception_as():
    return SameExceptionAs


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def create_random_session(create_random_string):
    return lambda: AgentSession(
        id=create_random_string(),
        history=(AgentTurn(create_random_string(), create_random_string()),),
        run_id=create_random_string())
