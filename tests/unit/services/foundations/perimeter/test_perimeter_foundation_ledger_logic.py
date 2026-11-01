# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The ledger foundation over typed records (principal review 2026-09-04, F-08).

A claim is written in flight under a lease, an outcome completes it, a thrown tool fails it, only
an in-flight claim is ever released, and compensation is recorded before and after the reversal.
"""

from unittest.mock import call


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
