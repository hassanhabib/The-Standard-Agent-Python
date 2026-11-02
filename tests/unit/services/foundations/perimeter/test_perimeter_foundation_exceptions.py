# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The reason these foundations exist.

Each resource failure must arrive named after its own resource; otherwise a full disk gets blamed
on the orchestration that happened to ask.
"""

from unittest.mock import ANY, call

import pytest

from restfulsense import HttpRequestException
from standard_agents.models.foundations.approvals.exceptions import (
    ApprovalDependencyException,
    FailedApprovalDependencyException)
from standard_agents.models.foundations.effect_ledgers.exceptions import (
    EffectLedgerDependencyException,
    FailedEffectLedgerDependencyException)
from standard_agents.models.foundations.policies.exceptions import (
    FailedPolicyDependencyException,
    FailedPolicyServiceException,
    PolicyDependencyException,
    PolicyServiceException)


async def test_should_throw_dependency_exception_on_authorize_if_policy_engine_is_unreachable(
        policy_service, policy_broker, logging_broker, create_random_effect, same_exception_as):

    # given
    random_effect = create_random_effect()
    http_request_exception = HttpRequestException()

    failed_policy_dependency_exception = FailedPolicyDependencyException(
        message="Failed policy dependency error occurred, contact support.",
        inner_exception=http_request_exception)

    expected_policy_dependency_exception = PolicyDependencyException(
        message="Policy dependency error occurred, contact support.",
        inner_exception=failed_policy_dependency_exception)

    policy_broker.authorize.side_effect = http_request_exception

    # when
    with pytest.raises(PolicyDependencyException) as raised:
        await policy_service.authorize_effect(random_effect)

    # then
    assert raised.value.same_exception_as(expected_policy_dependency_exception)
    assert policy_broker.mock_calls == [call.authorize(random_effect)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_policy_dependency_exception))]


async def test_should_throw_dependency_exception_on_request_approval_if_authority_is_unreachable(
        approval_service,
        approval_broker,
        logging_broker,
        create_random_effect,
        same_exception_as):
    """The most consequential of the three.

    An authority that cannot be reached is a dependency failure, never a verdict: a system that
    reads an outage as an answer will eventually read it as a yes.
    """

    # given
    random_effect = create_random_effect()
    http_request_exception = HttpRequestException()

    failed_approval_dependency_exception = FailedApprovalDependencyException(
        message="Failed approval dependency error occurred, contact support.",
        inner_exception=http_request_exception)

    expected_approval_dependency_exception = ApprovalDependencyException(
        message="Approval dependency error occurred, contact support.",
        inner_exception=failed_approval_dependency_exception)

    approval_broker.request.side_effect = http_request_exception

    # when
    with pytest.raises(ApprovalDependencyException) as raised:
        await approval_service.request_approval(random_effect)

    # then
    assert raised.value.same_exception_as(expected_approval_dependency_exception)
    assert approval_broker.mock_calls == [call.request(random_effect)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_approval_dependency_exception))]


async def test_should_throw_dependency_exception_on_record_outcome_if_disk_is_full(
        effect_ledger_service,
        effect_ledger_broker,
        logging_broker,
        create_random_string,
        create_random_effect,
        same_exception_as):
    """The failure that started the whole alignment: a full disk in the file-backed ledger,
    surfacing unmapped and attributed to Direction.
    """

    # given
    random_effect = create_random_effect()
    random_outcome = create_random_string()
    io_error = OSError()

    failed_effect_ledger_dependency_exception = FailedEffectLedgerDependencyException(
        message="Failed effect ledger dependency error occurred, contact support.",
        inner_exception=io_error)

    expected_effect_ledger_dependency_exception = EffectLedgerDependencyException(
        message="Effect ledger dependency error occurred, contact support.",
        inner_exception=failed_effect_ledger_dependency_exception)

    # What a loose mock answers for a select nobody set up: no record.
    effect_ledger_broker.select_record.return_value = None
    effect_ledger_broker.update_record.side_effect = io_error

    # when
    with pytest.raises(EffectLedgerDependencyException) as raised:
        await effect_ledger_service.record_outcome(random_effect, random_outcome)

    # then
    assert raised.value.same_exception_as(expected_effect_ledger_dependency_exception)

    assert effect_ledger_broker.mock_calls == [
        call.select_record(random_effect.idempotency_key),
        call.update_record(ANY)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_effect_ledger_dependency_exception))]


async def test_should_throw_critical_dependency_exception_on_claim_effect_if_access_denied(
        effect_ledger_service,
        effect_ledger_broker,
        time_broker,
        logging_broker,
        create_random_effect,
        create_random_date_time,
        same_exception_as):

    # given
    random_effect = create_random_effect()
    unauthorized_access_error = PermissionError()
    time_broker.get_current_date_time.return_value = create_random_date_time()

    failed_effect_ledger_dependency_exception = FailedEffectLedgerDependencyException(
        message="Failed effect ledger dependency error occurred, contact support.",
        inner_exception=unauthorized_access_error)

    expected_effect_ledger_dependency_exception = EffectLedgerDependencyException(
        message="Effect ledger dependency error occurred, contact support.",
        inner_exception=failed_effect_ledger_dependency_exception)

    effect_ledger_broker.insert_claim.side_effect = unauthorized_access_error

    # when
    with pytest.raises(EffectLedgerDependencyException) as raised:
        await effect_ledger_service.claim_effect(random_effect)

    # then
    assert raised.value.same_exception_as(expected_effect_ledger_dependency_exception)
    assert effect_ledger_broker.mock_calls == [call.insert_claim(ANY)]

    assert logging_broker.mock_calls == [
        call.log_critical(same_exception_as(expected_effect_ledger_dependency_exception))]


async def test_should_throw_service_exception_on_authorize_if_service_error_occurs(
        policy_service, policy_broker, logging_broker, create_random_effect, same_exception_as):

    # given
    random_effect = create_random_effect()
    service_error = Exception()

    failed_policy_service_exception = FailedPolicyServiceException(
        message="Failed policy service error occurred, contact support.",
        inner_exception=service_error)

    expected_policy_service_exception = PolicyServiceException(
        message="Policy service error occurred, contact support.",
        inner_exception=failed_policy_service_exception)

    policy_broker.authorize.side_effect = service_error

    # when
    with pytest.raises(PolicyServiceException) as raised:
        await policy_service.authorize_effect(random_effect)

    # then
    assert raised.value.same_exception_as(expected_policy_service_exception)
    assert policy_broker.mock_calls == [call.authorize(random_effect)]

    assert logging_broker.mock_calls == [
        call.log_error(same_exception_as(expected_policy_service_exception))]
