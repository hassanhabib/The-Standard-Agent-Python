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


TIER_BELOW = {
    "managements": "coordinations",
    "coordinations": "orchestrations",
    "orchestrations": "foundations",
}


def test_should_depend_only_on_the_tier_directly_below_it(service_above_foundations, tier_map):
    """The other half of the same rule: two or three of the tier DIRECTLY below.

    Reaching further down is not a lesser version of the same mistake, it is a different one.
    A count can be satisfied by anything; adjacency is what keeps a nature's foundations
    reachable only through that nature. DirectionCoordinationService held Decision's Gate for
    screen_tool_output and satisfied every other rule here while doing it (three dependencies,
    no broker), which is why this one had to be written down separately.
    """
    # given
    service_name = service_above_foundations.__name__

    [tier] = [
        name for name in TIER_BELOW
        if f".services.{name}" in service_above_foundations.__module__]

    permitted = f".services.{TIER_BELOW[tier]}"

    # when
    reached_past_it = sorted({
        dependency.__name__
        for constructor in tier_map.constructors(service_above_foundations)
        for dependency in tier_map.dependencies_in(constructor)
        if permitted not in dependency.__module__})

    # then
    assert reached_past_it == [], (
        f"{service_name} is a {tier[:-1]} service, so it composes {TIER_BELOW[tier]} and "
        f"nothing else: it takes [{', '.join(reached_past_it)}]. A service that reaches past the "
        "tier below it borrows another nature's internals, and no test of counts or brokers "
        "will ever see it.")


def test_should_hold_no_naked_delegate_in_any_service_constructor(tier_service, tier_map):
    """The counting escape the sweep demonstrated.

    Replace any service with a Callable and the dependency vanishes from every count above. A
    delegate that participates in a service's decisions is a collaborator, and a collaborator
    the count cannot see belongs inside a named model under models/ (policy is Data), where its
    arrival is a reviewed diff.
    """
    # given
    service_name = tier_service.__name__

    # when
    naked_delegates = sorted({
        parameter.name
        for constructor in tier_map.constructors(tier_service)
        for parameter in constructor
        if tier_map.carries_a_delegate(parameter.annotation)})

    # then
    assert naked_delegates == [], (
        f"{service_name} takes [{', '.join(naked_delegates)}]: a delegate that participates in "
        "a service's decisions is a collaborator the dependency count cannot see. Policy is "
        "Data: carry it inside a named model under models/, where its arrival is a reviewed "
        "diff rather than constructor sprawl")


def test_should_take_no_broker_above_the_foundation_tier_beyond_the_utilities(
        service_above_foundations, tier_map):
    """A tier that reaches a broker skips the foundation beneath it.

    That foundation is what would have given it validation, exception mapping and attribution.
    Skipping it is how a full disk came to be blamed on Direction.
    """
    # given
    service_name = service_above_foundations.__name__

    # when
    resource_brokers = sorted(
        tier_map.brokers_taken_by(service_above_foundations) - tier_map.utility_brokers)

    # then
    assert resource_brokers == [], (
        f"{service_name} sits above the foundation tier and takes "
        f"[{', '.join(resource_brokers)}]. A resource reached from here has no validation, no "
        "exception mapping, and its failures are attributed to the caller rather than to the "
        "resource.")


def test_should_not_let_any_broker_depend_on_a_nature_broker(tier_map):
    """The one at the bottom, and the last to be noticed. Invariant 3: brokers are thin.

    Stated precisely, because two shapes look like violations and are not: a broker MUST NOT
    hold a NATURE broker other than the one it implements.

    A nature broker is defined here as one a foundation wraps, derived from the foundations
    themselves rather than listed, so the rule cannot drift as foundations are added. That
    leaves exactly two legitimate shapes: a decorator holding its own contract plus the
    cross-cutting broker it applies (redaction, retry), and observability composing a clock and
    a sink. Neither can change what the agent decides or does, which is precisely why neither
    can become the hole that Policy, Approval and the effect ledger slipped through.
    """
    # given
    # Derived sets can empty out silently: a renamed module and this rule passes vacuously
    # forever. A derivation that finds nothing is a broken derivation, not a clean architecture.
    nature_brokers = frozenset(
        broker
        for service in tier_map.services_under("foundations")
        for broker in tier_map.brokers_taken_by(service)
        if broker not in tier_map.utility_brokers)

    brokers = tier_map.brokers()

    # when
    offenders = []

    for broker in brokers:
        implemented = {
            tier_map.role(contract.__name__)
            for contract in tier_map.broker_contracts_implemented_by(broker)}

        foreign = sorted(
            taken for taken in tier_map.brokers_taken_by(broker)
            if taken in nature_brokers and taken not in implemented)

        if foreign:
            offenders.append(f"{broker.__name__} takes [{', '.join(foreign)}]")

    # then
    assert offenders == [], (
        "a broker is a thin liaison to ONE resource (Invariant 3). A broker that reaches another "
        "nature's resource has business flow in it, and it is the hardest kind to see because "
        "it sits underneath everything else.")


def test_should_check_every_service_tier_that_exists(tier_map):
    """A tier nobody lists is a tier nobody checks: once a comment, now a rule.

    Every package under standard_agents.services must be one of the four checked tiers. When the
    loop moved to managements, it left every rule in this module for as long as nobody noticed,
    and a future tier gets no such window.
    """
    # given
    checked_tiers = {"foundations", "orchestrations", "coordinations", "managements"}

    # when
    actual_tiers = set(tier_map.service_tiers())

    # then
    assert actual_tiers <= checked_tiers, (
        f"[{', '.join(sorted(actual_tiers - checked_tiers))}] is a tier absent from the checked "
        "list, and a tier absent from the checked list is a tier nobody is checking, which is "
        "how the loop's move to managements went unwatched")
