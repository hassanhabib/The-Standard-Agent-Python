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
