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
    PolicyDependencyException,
    PolicyServiceException)
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
            # The broker's decision, unchanged. A foundation that softened a denial would be
            # deciding policy, which is not its job.
            return await self.policy_broker.authorize(effect)


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except HttpRequestException as http_request_exception:
        raise await _create_and_log_dependency_exception(
            logging_broker, http_request_exception)
    except Exception as exception:
        failed_policy_service_exception = FailedPolicyServiceException(
            message="Failed policy service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_policy_service_exception)


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
