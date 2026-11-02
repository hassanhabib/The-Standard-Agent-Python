# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The three perimeter foundations share one job: turn a resource failure into a failure named
after the resource. They are tested together because that is the property, and it is the same
property three times.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.approvals.approval_broker import ApprovalBroker
from standard_agents.brokers.effects.effect_ledger_broker import EffectLedgerBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.policies.policy_broker import PolicyBroker
from standard_agents.brokers.times.time_broker import TimeBroker
from standard_agents.models.brokers.effects.effect_record import EffectRecord
from standard_agents.models.brokers.effects.effect_state import EffectState
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.services.foundations.approvals.approval_service import ApprovalService
from standard_agents.services.foundations.effect_ledgers.effect_ledger_service import (
    EffectLedgerService)
from standard_agents.services.foundations.policies.policy_service import PolicyService
from xeptions import Xeption

LEASE = timedelta(minutes=5)


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
def approval_broker() -> ApprovalBroker:
    return create_autospec(ApprovalBroker, instance=True)


@pytest.fixture
def effect_ledger_broker() -> EffectLedgerBroker:
    return create_autospec(EffectLedgerBroker, instance=True)


@pytest.fixture
def time_broker() -> TimeBroker:
    return create_autospec(TimeBroker, instance=True)


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def policy_service(policy_broker, logging_broker) -> PolicyService:
    return PolicyService(policy_broker=policy_broker, logging_broker=logging_broker)


@pytest.fixture
def approval_service(approval_broker, logging_broker) -> ApprovalService:
    return ApprovalService(approval_broker=approval_broker, logging_broker=logging_broker)


@pytest.fixture
def effect_ledger_service(effect_ledger_broker, time_broker, logging_broker) -> EffectLedgerService:
    return EffectLedgerService(
        effect_ledger_broker=effect_ledger_broker,
        time_broker=time_broker,
        logging_broker=logging_broker,
        lease=LEASE)


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


@pytest.fixture
def create_random_date_time():
    return lambda: (
        datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
        + timedelta(minutes=random.randint(1, 999)))


@pytest.fixture
def create_in_flight_record():
    return lambda effect, claimed_on: EffectRecord(
        idempotency_key=effect.idempotency_key,
        tool_name=effect.tool_name,
        state=EffectState.IN_FLIGHT,
        owner=effect.run_id,
        claimed_on=claimed_on,
        lease_until=claimed_on + LEASE)
