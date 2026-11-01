# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The ledger foundation over typed records (principal review 2026-09-04, F-08).

A claim is written in flight under a lease, an outcome completes it, a thrown tool fails it, only
an in-flight claim is ever released, and compensation is recorded before and after the reversal.
"""

import dataclasses
from datetime import timedelta
from unittest.mock import ANY, call

from standard_agents.models.brokers.effects.effect_state import EffectState


async def test_should_claim_effect(
        effect_ledger_service,
        effect_ledger_broker,
        time_broker,
        logging_broker,
        create_random_effect,
        create_random_date_time,
        create_in_flight_record):

    # given: a first-time act
    random_effect = create_random_effect()
    random_date_time = create_random_date_time()
    expected_claim = create_in_flight_record(random_effect, random_date_time)
    time_broker.get_current_date_time.return_value = random_date_time
    effect_ledger_broker.insert_claim.return_value = True

    # when
    actual_prior = await effect_ledger_service.claim_effect(random_effect)

    # then: None means proceed; the claim written is in flight, owned, stamped and leased
    assert actual_prior is None
    assert effect_ledger_broker.mock_calls == [call.insert_claim(expected_claim)]
    assert logging_broker.mock_calls == []


async def test_should_retrieve_prior_record_on_claim_effect_if_act_was_seen_before(
        effect_ledger_service,
        effect_ledger_broker,
        time_broker,
        logging_broker,
        create_random_string,
        create_random_effect,
        create_random_date_time,
        create_in_flight_record):

    # given: the key already has a record
    random_effect = create_random_effect()
    random_date_time = create_random_date_time()

    prior_record = dataclasses.replace(
        create_in_flight_record(random_effect, random_date_time),
        state=EffectState.COMPLETED,
        outcome=create_random_string())

    expected_record = prior_record
    time_broker.get_current_date_time.return_value = random_date_time
    effect_ledger_broker.insert_claim.return_value = False
    effect_ledger_broker.select_record.return_value = prior_record

    # when
    actual_record = await effect_ledger_service.claim_effect(random_effect)

    # then: the prior record comes back whole; what it means is the tier above's judgment
    assert actual_record == expected_record

    assert effect_ledger_broker.mock_calls == [
        call.insert_claim(ANY),
        call.select_record(random_effect.idempotency_key)]

    assert logging_broker.mock_calls == []


async def test_should_record_outcome(
        effect_ledger_service,
        effect_ledger_broker,
        time_broker,
        logging_broker,
        create_random_string,
        create_random_effect,
        create_random_date_time,
        create_in_flight_record):

    # given: an in-flight claim, completed with what the act produced
    random_effect = create_random_effect()
    random_outcome = create_random_string()
    claimed_on = create_random_date_time()
    recorded_on = claimed_on + timedelta(seconds=3)
    in_flight_record = create_in_flight_record(random_effect, claimed_on)

    expected_record = dataclasses.replace(
        in_flight_record,
        state=EffectState.COMPLETED,
        outcome=random_outcome,
        detail=None,
        recorded_on=recorded_on)

    time_broker.get_current_date_time.return_value = recorded_on
    effect_ledger_broker.select_record.return_value = in_flight_record

    # when
    await effect_ledger_service.record_outcome(random_effect, random_outcome)

    # then
    assert effect_ledger_broker.mock_calls == [
        call.select_record(random_effect.idempotency_key),
        call.update_record(expected_record)]

    assert logging_broker.mock_calls == []


async def test_should_record_failure(
        effect_ledger_service,
        effect_ledger_broker,
        time_broker,
        logging_broker,
        create_random_string,
        create_random_effect,
        create_random_date_time,
        create_in_flight_record):

    # given: the tool threw; the act's fate is unknown and the record says so
    random_effect = create_random_effect()
    random_detail = create_random_string()
    claimed_on = create_random_date_time()
    recorded_on = claimed_on + timedelta(seconds=3)
    in_flight_record = create_in_flight_record(random_effect, claimed_on)

    expected_record = dataclasses.replace(
        in_flight_record,
        state=EffectState.FAILED,
        outcome=None,
        detail=random_detail,
        recorded_on=recorded_on)

    time_broker.get_current_date_time.return_value = recorded_on
    effect_ledger_broker.select_record.return_value = in_flight_record

    # when
    await effect_ledger_service.record_failure(random_effect, random_detail)

    # then
    assert effect_ledger_broker.mock_calls == [
        call.select_record(random_effect.idempotency_key),
        call.update_record(expected_record)]

    assert logging_broker.mock_calls == []


async def test_should_release_claim_if_record_is_in_flight(
        effect_ledger_service,
        effect_ledger_broker,
        logging_broker,
        create_random_effect,
        create_random_date_time,
        create_in_flight_record):

    # given: a held act, claimed and never performed
    random_effect = create_random_effect()
    in_flight_record = create_in_flight_record(random_effect, create_random_date_time())
    effect_ledger_broker.select_record.return_value = in_flight_record

    # when
    await effect_ledger_service.release_claim(random_effect)

    # then
    assert effect_ledger_broker.mock_calls == [
        call.select_record(random_effect.idempotency_key),
        call.delete_record(random_effect.idempotency_key)]

    assert logging_broker.mock_calls == []


async def test_should_not_release_claim_if_record_is_not_in_flight(
        effect_ledger_service,
        effect_ledger_broker,
        logging_broker,
        create_random_string,
        create_random_effect,
        create_random_date_time,
        create_in_flight_record):
    """A record with an outcome names an act that happened; releasing it would turn run-once
    back into run-again.
    """

    # given
    random_effect = create_random_effect()

    completed_record = dataclasses.replace(
        create_in_flight_record(random_effect, create_random_date_time()),
        state=EffectState.COMPLETED,
        outcome=create_random_string())

    effect_ledger_broker.select_record.return_value = completed_record

    # when
    await effect_ledger_service.release_claim(random_effect)

    # then
    assert effect_ledger_broker.mock_calls == [
        call.select_record(random_effect.idempotency_key)]

    assert logging_broker.mock_calls == []


async def test_should_record_compensation_intent(
        effect_ledger_service,
        effect_ledger_broker,
        time_broker,
        logging_broker,
        create_random_string,
        create_random_effect,
        create_random_date_time,
        create_in_flight_record):

    # given: a completed act about to be undone; the intent goes on the record first
    random_effect = create_random_effect()
    claimed_on = create_random_date_time()
    recorded_on = claimed_on + timedelta(seconds=9)

    completed_record = dataclasses.replace(
        create_in_flight_record(random_effect, claimed_on),
        state=EffectState.COMPLETED,
        outcome=create_random_string())

    expected_record = dataclasses.replace(
        completed_record,
        state=EffectState.COMPENSATION_PENDING,
        recorded_on=recorded_on)

    time_broker.get_current_date_time.return_value = recorded_on
    effect_ledger_broker.select_record.return_value = completed_record

    # when
    await effect_ledger_service.record_compensation_intent(random_effect.idempotency_key)

    # then
    assert effect_ledger_broker.mock_calls == [
        call.select_record(random_effect.idempotency_key),
        call.update_record(expected_record)]

    assert logging_broker.mock_calls == []


async def test_should_record_compensation(
        effect_ledger_service,
        effect_ledger_broker,
        time_broker,
        logging_broker,
        create_random_string,
        create_random_effect,
        create_random_date_time,
        create_in_flight_record):

    # given: the reversal happened, and how it happened is written against the same record
    random_effect = create_random_effect()
    random_detail = create_random_string()
    claimed_on = create_random_date_time()
    recorded_on = claimed_on + timedelta(seconds=12)

    pending_record = dataclasses.replace(
        create_in_flight_record(random_effect, claimed_on),
        state=EffectState.COMPENSATION_PENDING,
        outcome=create_random_string())

    expected_record = dataclasses.replace(
        pending_record,
        state=EffectState.COMPENSATED,
        detail=random_detail,
        recorded_on=recorded_on)

    time_broker.get_current_date_time.return_value = recorded_on
    effect_ledger_broker.select_record.return_value = pending_record

    # when
    await effect_ledger_service.record_compensation(
        random_effect.idempotency_key, random_detail)

    # then
    assert effect_ledger_broker.mock_calls == [
        call.select_record(random_effect.idempotency_key),
        call.update_record(expected_record)]

    assert logging_broker.mock_calls == []
