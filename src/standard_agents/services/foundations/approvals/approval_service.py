# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from restfulsense import HttpRequestException
from standard_agents.brokers.approvals.approval_broker import ApprovalBroker, ApprovalDecision
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.foundations.approvals.exceptions import (
    ApprovalDependencyException,
    ApprovalServiceException,
    ApprovalValidationException,
    FailedApprovalDependencyException,
    FailedApprovalServiceException,
    InvalidApprovalException)
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect


class ApprovalService:
    """Human approval, as a foundation.

    This one matters most of the three. An approval broker reaches a person (a queue, a ticket, a
    chat prompt) and when that is unreachable the honest answer is a dependency failure, never a
    decision. A raw exception escaping into Direction risks being read as "not approved", and a
    system that treats an outage as a verdict is a system that will one day treat it as a yes.
    """

    def __init__(self, *, approval_broker: ApprovalBroker, logging_broker: LoggingBroker) -> None:
        self.approval_broker = approval_broker
        self.logging_broker = logging_broker

    async def request_approval(self, effect: AgentEffect) -> ApprovalDecision:
        """Asks an authority to permit this act. PENDING is not consent (SPEC.md 4.9)."""
        async with _handling_exceptions(self.logging_broker):
            _validate_effect(effect)

            # PENDING must survive the trip untouched. Turning an unanswered request into
            # anything else here is the one mistake that would let silence look like consent.
            return await self.approval_broker.request(effect)


def _validate_effect(effect: AgentEffect | None) -> None:
    """An act with no name cannot be judged.

    Judging it anyway would return a decision about nothing that the perimeter would then act on
    (SPEC.md 4.9).
    """
    if effect is None or not effect.tool_name or effect.tool_name.isspace():
        raise InvalidApprovalException(
            message="Invalid approval. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidApprovalException as invalid_approval_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_approval_exception)
    except PermissionError as permission_error:
        raise await _create_and_log_critical_dependency_exception(
            logging_broker, permission_error)
    except OSError as os_error:
        raise await _create_and_log_dependency_exception(logging_broker, os_error)
    except HttpRequestException as http_request_exception:
        raise await _create_and_log_dependency_exception(
            logging_broker, http_request_exception)
    except Exception as exception:
        failed_approval_service_exception = FailedApprovalServiceException(
            message="Failed approval service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_approval_service_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ApprovalValidationException:

    approval_validation_exception = ApprovalValidationException(
        message="Approval validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(approval_validation_exception)

    return approval_validation_exception


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ApprovalDependencyException:

    approval_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_critical(approval_dependency_exception)

    return approval_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ApprovalDependencyException:

    approval_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(approval_dependency_exception)

    return approval_dependency_exception


def _create_dependency_exception(exception: Exception) -> ApprovalDependencyException:
    failed_approval_dependency_exception = FailedApprovalDependencyException(
        message="Failed approval dependency error occurred, contact support.",
        inner_exception=exception)

    return ApprovalDependencyException(
        message="Approval dependency error occurred, contact support.",
        inner_exception=failed_approval_dependency_exception)


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ApprovalServiceException:

    approval_service_exception = ApprovalServiceException(
        message="Approval service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(approval_service_exception)

    return approval_service_exception
