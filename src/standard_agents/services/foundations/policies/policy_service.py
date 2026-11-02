# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from restfulsense import HttpRequestException
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.policies.policy_broker import PolicyBroker
from standard_agents.models.foundations.policies.exceptions import (
    FailedPolicyDependencyException,
    FailedPolicyServiceException,
    InvalidPolicyException,
    PolicyDependencyException,
    PolicyServiceException,
    PolicyValidationException)
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision)


class PolicyService:
    """Authorization, as a foundation rather than as a broker reached from Direction.

    A policy engine is usually somewhere else: a rules service, an OPA sidecar, a database. When
    it is unreachable, that has to arrive as a POLICY failure. Reached directly from Direction it
    arrived as an unmapped HttpRequestException blamed on the orchestration, which is a trace that
    sends someone to read the wrong code (docs/architecture-alignment.md).
    """

    def __init__(self, *, policy_broker: PolicyBroker, logging_broker: LoggingBroker) -> None:
        self.policy_broker = policy_broker
        self.logging_broker = logging_broker

    async def authorize_effect(self, effect: AgentEffect) -> AuthorizationDecision:
        """May this act happen, and if not, why not (SPEC.md 4.9)?"""
        async with _handling_exceptions(self.logging_broker):
            _validate_effect(effect)

            # The broker's decision, unchanged. A foundation that softened a denial would be
            # deciding policy, which is not its job.
            return await self.policy_broker.authorize(effect)


def _validate_effect(effect: AgentEffect | None) -> None:
    """An act with no name cannot be judged.

    Judging it anyway would return a decision about nothing that the perimeter would then act on
    (SPEC.md 4.9).
    """
    if effect is None or not effect.tool_name or effect.tool_name.isspace():
        raise InvalidPolicyException(
            message="Invalid policy. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidPolicyException as invalid_policy_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_policy_exception)
    except PermissionError as permission_error:
        raise await _create_and_log_critical_dependency_exception(
            logging_broker, permission_error)
    except OSError as os_error:
        raise await _create_and_log_dependency_exception(logging_broker, os_error)
    except HttpRequestException as http_request_exception:
        raise await _create_and_log_dependency_exception(
            logging_broker, http_request_exception)
    except Exception as exception:
        failed_policy_service_exception = FailedPolicyServiceException(
            message="Failed policy service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_policy_service_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> PolicyValidationException:

    policy_validation_exception = PolicyValidationException(
        message="Policy validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(policy_validation_exception)

    return policy_validation_exception


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> PolicyDependencyException:

    policy_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_critical(policy_dependency_exception)

    return policy_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> PolicyDependencyException:

    policy_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(policy_dependency_exception)

    return policy_dependency_exception


def _create_dependency_exception(exception: Exception) -> PolicyDependencyException:
    failed_policy_dependency_exception = FailedPolicyDependencyException(
        message="Failed policy dependency error occurred, contact support.",
        inner_exception=exception)

    return PolicyDependencyException(
        message="Policy dependency error occurred, contact support.",
        inner_exception=failed_policy_dependency_exception)


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> PolicyServiceException:

    policy_service_exception = PolicyServiceException(
        message="Policy service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(policy_service_exception)

    return policy_service_exception
