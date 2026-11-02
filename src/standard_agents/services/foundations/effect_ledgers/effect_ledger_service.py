# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from restfulsense import HttpRequestException
from standard_agents.brokers.effects.effect_ledger_broker import EffectLedgerBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.times.time_broker import TimeBroker
from standard_agents.models.brokers.effects.effect_record import EffectRecord
from standard_agents.models.brokers.effects.effect_state import EffectState
from standard_agents.models.foundations.effect_ledgers.exceptions import (
    EffectLedgerDependencyException,
    EffectLedgerServiceException,
    EffectLedgerValidationException,
    FailedEffectLedgerDependencyException,
    FailedEffectLedgerServiceException,
    InvalidEffectLedgerException)
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect


class EffectLedgerService:
    """The ledger of which acts have run, over typed records (SPEC.md 4.9)."""

    def __init__(
            self,
            *,
            effect_ledger_broker: EffectLedgerBroker,
            time_broker: TimeBroker,
            logging_broker: LoggingBroker,
            lease: timedelta) -> None:

        self.effect_ledger_broker = effect_ledger_broker
        self.time_broker = time_broker
        self.logging_broker = logging_broker

        # How long an in-flight claim is presumed live. Past it, a claim with no outcome is an
        # earlier attempt whose fate is unknown, and a repeat is held for reconciliation rather
        # than presumed either way (principal review 2026-09-04, F-08). The deployment sets it,
        # because only the deployment knows how long its tools take.
        self.lease = lease

    async def claim_effect(self, effect: AgentEffect) -> EffectRecord | None:
        """Claims this act for its run, in flight, under a lease.

        Reports the prior record when the key already has one, and None when this is the first
        time and the caller should proceed (SPEC.md 4.9).
        """
        async with _handling_exceptions(self.logging_broker):
            _validate_effect(effect)
            now = self.time_broker.get_current_date_time()

            claim = EffectRecord(
                idempotency_key=effect.idempotency_key,
                tool_name=effect.tool_name,
                state=EffectState.IN_FLIGHT,
                owner=effect.run_id,
                claimed_on=now,
                lease_until=now + self.lease)

            claimed = await self.effect_ledger_broker.insert_claim(claim)

            # None means this act has not run and the caller should proceed. It has to stay
            # distinct from a read that failed: one means go, the other means stop.
            if claimed:
                return None

            return await self.effect_ledger_broker.select_record(effect.idempotency_key)

    async def record_outcome(self, effect: AgentEffect, outcome: str) -> None:
        """Records what the act produced, before the loop advances: the record is completed."""
        async with _handling_exceptions(self.logging_broker):
            _validate_effect(effect)

            await self._update(
                effect.idempotency_key,
                effect.tool_name,
                effect.run_id,
                EffectState.COMPLETED,
                outcome=outcome,
                detail=None)

    async def record_failure(self, effect: AgentEffect, detail: str) -> None:
        """Records that the tool threw.

        Whether the world changed is unknown, so the record is failed rather than released, and
        a repeat is held for reconciliation.
        """
        async with _handling_exceptions(self.logging_broker):
            _validate_effect(effect)

            await self._update(
                effect.idempotency_key,
                effect.tool_name,
                effect.run_id,
                EffectState.FAILED,
                outcome=None,
                detail=detail)

    async def release_claim(self, effect: AgentEffect) -> None:
        """Gives back the claim on an act that was held rather than performed.

        Only an unfinished claim is given back. A record with an outcome, a failure or a
        compensation names an act that happened, and forgetting that would turn run-once back
        into run-again.
        """
        async with _handling_exceptions(self.logging_broker):
            _validate_effect(effect)
            record = await self.effect_ledger_broker.select_record(effect.idempotency_key)

            if record is not None and record.state is EffectState.IN_FLIGHT:
                await self.effect_ledger_broker.delete_record(effect.idempotency_key)

    async def record_compensation_intent(self, idempotency_key: str) -> None:
        """Records that compensation was decided, before it is attempted."""
        async with _handling_exceptions(self.logging_broker):
            _validate_key(idempotency_key)
            record = await self.effect_ledger_broker.select_record(idempotency_key)
            _validate_record_exists(record)

            await self.effect_ledger_broker.update_record(dataclasses.replace(
                record,
                state=EffectState.COMPENSATION_PENDING,
                recorded_on=self.time_broker.get_current_date_time()))

    async def record_compensation(self, idempotency_key: str, detail: str) -> None:
        """Records that the act was undone, and how."""
        async with _handling_exceptions(self.logging_broker):
            _validate_key(idempotency_key)
            record = await self.effect_ledger_broker.select_record(idempotency_key)
            _validate_record_exists(record)

            await self.effect_ledger_broker.update_record(dataclasses.replace(
                record,
                state=EffectState.COMPENSATED,
                detail=detail,
                recorded_on=self.time_broker.get_current_date_time()))

    async def _update(
            self,
            idempotency_key: str,
            tool_name: str,
            owner: str,
            state: EffectState,
            *,
            outcome: str | None,
            detail: str | None) -> None:
        """Completes the record in place when the claim is there, and writes it whole when not.

        A ledger that lost the claim still gets the outcome, which is the fact that matters.
        """
        now = self.time_broker.get_current_date_time()
        record = await self.effect_ledger_broker.select_record(idempotency_key)

        if record is None:
            record = EffectRecord(
                idempotency_key=idempotency_key,
                tool_name=tool_name,
                owner=owner,
                claimed_on=now,
                lease_until=now)

        await self.effect_ledger_broker.update_record(dataclasses.replace(
            record,
            state=state,
            outcome=outcome,
            detail=detail,
            recorded_on=now))


def _validate_effect(effect: AgentEffect | None) -> None:
    """An act with no name cannot be judged.

    Judging it anyway would return a decision about nothing that the perimeter would then act on
    (SPEC.md 4.9).
    """
    if effect is None or not effect.tool_name or effect.tool_name.isspace():
        raise InvalidEffectLedgerException(
            message="Invalid effect ledger. Please correct the error and try again.")


def _validate_key(idempotency_key: str | None) -> None:
    if not idempotency_key or idempotency_key.isspace():
        raise InvalidEffectLedgerException(
            message="Invalid effect ledger. Please correct the error and try again.")


def _validate_record_exists(record: EffectRecord | None) -> None:
    """Compensation is recorded against an act the ledger knows.

    Marking an act it never saw would invent a history for it.
    """
    if record is None:
        raise InvalidEffectLedgerException(
            message="Invalid effect ledger. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidEffectLedgerException as invalid_effect_ledger_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_effect_ledger_exception)
    except PermissionError as permission_error:
        raise await _create_and_log_critical_dependency_exception(
            logging_broker, permission_error)
    except OSError as os_error:
        raise await _create_and_log_dependency_exception(logging_broker, os_error)
    except HttpRequestException as http_request_exception:
        raise await _create_and_log_dependency_exception(
            logging_broker, http_request_exception)
    except Exception as exception:
        failed_effect_ledger_service_exception = FailedEffectLedgerServiceException(
            message="Failed effect ledger service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_effect_ledger_service_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> EffectLedgerValidationException:

    effect_ledger_validation_exception = EffectLedgerValidationException(
        message="Effect ledger validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(effect_ledger_validation_exception)

    return effect_ledger_validation_exception


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> EffectLedgerDependencyException:

    effect_ledger_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_critical(effect_ledger_dependency_exception)

    return effect_ledger_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> EffectLedgerDependencyException:

    effect_ledger_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(effect_ledger_dependency_exception)

    return effect_ledger_dependency_exception


def _create_dependency_exception(exception: Exception) -> EffectLedgerDependencyException:
    failed_effect_ledger_dependency_exception = FailedEffectLedgerDependencyException(
        message="Failed effect ledger dependency error occurred, contact support.",
        inner_exception=exception)

    return EffectLedgerDependencyException(
        message="Effect ledger dependency error occurred, contact support.",
        inner_exception=failed_effect_ledger_dependency_exception)


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> EffectLedgerServiceException:

    effect_ledger_service_exception = EffectLedgerServiceException(
        message="Effect ledger service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(effect_ledger_service_exception)

    return effect_ledger_service_exception
