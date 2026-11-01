# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The three perimeter foundations share one job: turn a resource failure into a failure named
after the resource. They are tested together because that is the property, and it is the same
property three times.
"""

import uuid
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.policies.policy_broker import PolicyBroker
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.services.foundations.policies.policy_service import PolicyService
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
def policy_broker() -> PolicyBroker:
    return create_autospec(PolicyBroker, instance=True)


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def policy_service(policy_broker, logging_broker) -> PolicyService:
    return PolicyService(policy_broker=policy_broker, logging_broker=logging_broker)


@pytest.fixture
def same_exception_as():
    return SameExceptionAs


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def create_random_effect(create_random_string):
    return lambda: AgentEffect.create(
        run_id=create_random_string(),
        tool_name=create_random_string(),
        arguments=create_random_string())
