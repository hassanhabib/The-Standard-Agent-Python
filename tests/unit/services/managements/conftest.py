# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses
import uuid
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.telemetries.telemetry_broker import TelemetryBroker
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.services.coordinations.data.data_coordination_service import (
    DataCoordinationService)
from standard_agents.services.coordinations.decision.decision_coordination_service import (
    DecisionCoordinationService)
from standard_agents.services.coordinations.direction.direction_coordination_service import (
    DirectionCoordinationService)
from standard_agents.services.managements.run_management_service import RunManagementService
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
def data_coordination_service() -> DataCoordinationService:
    data_coordination_service = create_autospec(DataCoordinationService, instance=True)

    # A loose Moq mock answers an unarranged list with an empty one: the agent has no servers.
    data_coordination_service.retrieve_remote_tools.return_value = ()

    return data_coordination_service


@pytest.fixture
def decision_coordination_service() -> DecisionCoordinationService:
    return create_autospec(DecisionCoordinationService, instance=True)


@pytest.fixture
def direction_coordination_service() -> DirectionCoordinationService:
    return create_autospec(DirectionCoordinationService, instance=True)


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def telemetry_broker() -> TelemetryBroker:
    telemetry_broker = create_autospec(TelemetryBroker, instance=True)

    # A loose Moq mock answers an unarranged IDisposable with null: no scope to close.
    telemetry_broker.start_run.return_value = None
    telemetry_broker.start_turn.return_value = None

    return telemetry_broker


@pytest.fixture
def run_management_service(
        data_coordination_service,
        decision_coordination_service,
        direction_coordination_service,
        logging_broker) -> RunManagementService:

    return RunManagementService(
        data_coordination_service=data_coordination_service,
        decision_coordination_service=decision_coordination_service,
        direction_coordination_service=direction_coordination_service,
        logging_broker=logging_broker)


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def setup_orchestrations_pass_through(
        data_coordination_service,
        decision_coordination_service):

    def setup() -> None:
        data_coordination_service.recall.side_effect = lambda context: context
        decision_coordination_service.think.side_effect = lambda context: context

    return setup


@pytest.fixture
def setup_direction_terminates(direction_coordination_service):
    def setup(result: str) -> None:
        direction_coordination_service.act.side_effect = lambda context: dataclasses.replace(
            context, result=result, status=AgentStatus.RESPONDED)

    return setup


@pytest.fixture
def setup_direction_never_terminates(direction_coordination_service):
    def setup(result: str) -> None:
        direction_coordination_service.act.side_effect = lambda context: dataclasses.replace(
            context, result=result, status=AgentStatus.WORKING)

    return setup


@pytest.fixture
def same_exception_as():
    return SameExceptionAs
