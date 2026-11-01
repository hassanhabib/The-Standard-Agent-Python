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


def test_should_hold_two_or_three_dependencies(service_above_foundations, tier_map):
    """The 2-3 rule, which is the one that motivated the whole restructure.

    Every tier holds two or three of the tier directly below it: management over coordinations,
    coordination over orchestrations, orchestration over foundations.

    Both bounds have a cost. More than three means the service is doing too much and wants
    decomposition: that is what put six foundations under Direction. FEWER than two means the
    opposite: a service with one dependency composes nothing, so it is a pass-through that adds
    a layer and an exception hop for no work.

    Utility brokers do not count. They are held by every tier and none of them is a dependency
    in the sense the rule is about.
    """
    # given
    service_name = service_above_foundations.__name__

    # when
    counts = [
        len(tier_map.dependencies_in(constructor))
        for constructor in tier_map.constructors(service_above_foundations)]

    # then
    assert all(2 <= count <= 3 for count in counts), (
        f"{service_name} holds [{', '.join(map(str, counts))}] dependencies. Two or three is "
        "the rule at every tier: more and the service is doing too much, fewer and it composes "
        "nothing and is a layer for its own sake.")
