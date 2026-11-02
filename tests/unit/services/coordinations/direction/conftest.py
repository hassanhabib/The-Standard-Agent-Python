# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from datetime import timedelta
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.approvals.not_configured_approval_broker import (
    NotConfiguredApprovalBroker)
from standard_agents.brokers.effects.in_memory_effect_ledger_broker import (
    InMemoryEffectLedgerBroker)
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.policies.not_configured_policy_broker import (
    NotConfiguredPolicyBroker)
from standard_agents.brokers.times.system_time_broker import SystemTimeBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.coordinations.direction.direction_coordination_service import (
    DirectionCoordinationService)
from standard_agents.services.foundations.approvals.approval_service import ApprovalService
from standard_agents.services.foundations.effect_ledgers.effect_ledger_service import (
    EffectLedgerService)
from standard_agents.services.foundations.external_tools.external_tool_service import (
    ExternalToolService)
from standard_agents.services.foundations.internal_tools.internal_tool_service import (
    InternalToolService)
from standard_agents.services.foundations.policies.policy_service import PolicyService
from standard_agents.services.foundations.returns.return_service import ReturnService
from standard_agents.services.orchestrations.direction.executions.execution_orchestration_service \
    import ExecutionOrchestrationService
from standard_agents.services.orchestrations.direction.perimeters.perimeter_orchestration_service \
    import PerimeterOrchestrationService
from xeptions import Xeption


class SameExceptionAs:
    """Matches, in a recorded call, an exception equivalent to the expected one."""

    def __init__(self, expected_exception: Xeption) -> None:
        self.expected_exception = expected_exception

    def __eq__(self, actual_exception: object) -> bool:
        return self.expected_exception.same_exception_as(actual_exception)

    def __repr__(self) -> str:
        return f"SameExceptionAs({self.expected_exception!r})"


class Containing:
    """Matches, in a recorded call, a string containing the expected text (It.Is Contains)."""

    def __init__(self, expected_text: str) -> None:
        self.expected_text = expected_text

    def __eq__(self, actual_text: object) -> bool:
        return isinstance(actual_text, str) and self.expected_text in actual_text

    def __repr__(self) -> str:
        return f"Containing({self.expected_text!r})"


@pytest.fixture
def internal_tool_service() -> InternalToolService:
    return create_autospec(InternalToolService, instance=True)


@pytest.fixture
def external_tool_service() -> ExternalToolService:
    return create_autospec(ExternalToolService, instance=True)


@pytest.fixture
def return_service() -> ReturnService:
    return create_autospec(ReturnService, instance=True)


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def new_perimeter(logging_broker):
    """Real regions over the foundations, as the C# composes them for these tests."""
    return lambda: PerimeterOrchestrationService(
        policy_service=PolicyService(
            policy_broker=NotConfiguredPolicyBroker(),
            logging_broker=logging_broker),
        approval_service=ApprovalService(
            approval_broker=NotConfiguredApprovalBroker(),
            logging_broker=logging_broker),
        effect_ledger_service=EffectLedgerService(
            effect_ledger_broker=InMemoryEffectLedgerBroker(),
            time_broker=SystemTimeBroker(),
            logging_broker=logging_broker,
            lease=timedelta(minutes=5)),
        time_broker=SystemTimeBroker(),
        logging_broker=logging_broker)


@pytest.fixture
def new_execution(internal_tool_service, external_tool_service, return_service, logging_broker):
    return lambda: ExecutionOrchestrationService(
        internal_tool_service=internal_tool_service,
        external_tool_service=external_tool_service,
        return_service=return_service,
        logging_broker=logging_broker)


@pytest.fixture
def direction_coordination_service(
        new_perimeter,
        new_execution,
        logging_broker) -> DirectionCoordinationService:

    # Real regions over mocked foundations: the mocks sit where they sat before
    # regionalization, so every assertion is unchanged.
    return DirectionCoordinationService(
        perimeter_service=new_perimeter(),
        execution_service=new_execution(),
        logging_broker=logging_broker)


@pytest.fixture
def same_exception_as():
    return SameExceptionAs


@pytest.fixture
def containing():
    return Containing


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def create_context_with_direction(create_random_string):
    return lambda direction_type, payload: AgentContext(
        prompt=create_random_string(),
        direction_type=direction_type,
        payload=payload)
