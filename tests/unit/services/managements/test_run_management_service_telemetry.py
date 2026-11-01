# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import ANY, call

from standard_agents.services.managements.run_management_service import RunManagementService


async def test_should_emit_telemetry_across_the_run_and_its_turns(
        data_coordination_service,
        decision_coordination_service,
        direction_coordination_service,
        logging_broker,
        telemetry_broker,
        create_random_string,
        setup_orchestrations_pass_through,
        setup_direction_terminates):

    # given
    expected_answer = create_random_string()
    setup_orchestrations_pass_through()
    setup_direction_terminates(expected_answer)

    telemetered_run_management_service = RunManagementService(
        data_coordination_service=data_coordination_service,
        decision_coordination_service=decision_coordination_service,
        direction_coordination_service=direction_coordination_service,
        logging_broker=logging_broker,
        telemetry_broker=telemetry_broker)

    # when
    actual_answer = await telemetered_run_management_service.process_prompt(
        create_random_string())

    # then
    assert actual_answer == expected_answer

    assert telemetry_broker.mock_calls == [
        call.start_run(""),
        call.start_turn(0),
        call.record_turn_usage(ANY, ANY, ANY),
        call.record_run_outcome("Responded", ANY, ANY)]


async def test_should_record_the_outcome_when_turns_run_out(
        data_coordination_service,
        decision_coordination_service,
        direction_coordination_service,
        logging_broker,
        telemetry_broker,
        create_random_string,
        setup_orchestrations_pass_through,
        setup_direction_never_terminates):

    # given
    setup_orchestrations_pass_through()
    setup_direction_never_terminates(create_random_string())

    telemetered_run_management_service = RunManagementService(
        data_coordination_service=data_coordination_service,
        decision_coordination_service=decision_coordination_service,
        direction_coordination_service=direction_coordination_service,
        logging_broker=logging_broker,
        max_turns=2,
        telemetry_broker=telemetry_broker)

    # when
    await telemetered_run_management_service.process_prompt(create_random_string())

    # then
    assert telemetry_broker.start_turn.mock_calls == [call(ANY)] * 2

    # A capped run stopped mid-work and says so: the status recorded is Working, the same truth
    # the loop reports to the caller, never a Responded it did not earn.
    assert telemetry_broker.record_run_outcome.mock_calls == [call("Working", ANY, ANY)]
