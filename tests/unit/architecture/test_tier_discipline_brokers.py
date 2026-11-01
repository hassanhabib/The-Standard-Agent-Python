# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------


def test_should_hold_no_other_broker_unless_decorating_one(tier_map):
    """Found in the 2026-09-04 principal review (F-16).

    The logging broker held the time broker and the audit broker, orchestrated both, and the
    alignment document said no deviation remained. A broker is one resource, wrapped; brokers
    cannot call other brokers. The one shape that may hold a broker is a DECORATOR: a broker
    that implements the very interface it takes, so it wraps another broker's call and adds one
    concern (retry, redaction, audit) without owning a resource of its own. This reads the
    constructors, so the dependency FLOW is what is checked, not the package a class sits in.
    """
    # given
    offenders = []

    # when
    for broker in tier_map.brokers():
        implemented = tier_map.broker_contracts_implemented_by(broker)

        for constructor in tier_map.constructors(broker):
            taken = tier_map.broker_contracts_taken_by(constructor)
            decorates = any(contract in implemented for contract in taken)

            if taken and not decorates:
                offenders.append(
                    f"{broker.__name__} takes "
                    f"[{', '.join(contract.__name__ for contract in taken)}]")

    # then
    assert offenders == [], (
        "a broker is one resource, wrapped, and brokers cannot call other brokers; the only "
        "broker that may hold another is a decorator, which implements the interface it takes "
        "and adds one concern to the call it wraps")
