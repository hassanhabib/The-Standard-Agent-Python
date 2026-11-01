# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The Standard's tier rules, as a test rather than as a convention.

The enterprise program put five brokers where brokers are not allowed (an orchestration holding
three, coordination holding two, and a broker holding two more) and nothing failed. Every one of
those was invisible until someone read the constructors, which is exactly the kind of erosion a
build should catch (docs/architecture-alignment.md).

So: a foundation wraps ONE nature broker. Anything above the foundation tier holds no broker at
all. Utility brokers are the documented exception, and the list of them is short and named in
conftest.py so that adding a fifth is a reviewed decision rather than an omission nobody sees.
"""


def test_should_wrap_exactly_one_nature_broker_per_foundation(foundation_service, tier_map):
    # given
    service_name = foundation_service.__name__

    # when
    worst = max(
        (broker_set - tier_map.utility_brokers
         for broker_set in tier_map.broker_sets_taken_by(foundation_service)),
        key=len,
        default=frozenset())

    # then: ReturnService is the dead end and wraps none; everything else wraps exactly one.
    assert len(worst) <= 1, (
        f"{service_name} is a foundation, and a foundation wraps ONE broker: one of its "
        f"constructors takes [{', '.join(sorted(worst))}]. A second broker here is a capability "
        "that belongs in its own foundation, or a concern that belongs in a decorating broker "
        "at composition.")
