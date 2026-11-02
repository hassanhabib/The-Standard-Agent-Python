# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------


async def test_should_narrate_run_outcome_on_process_prompt(
        run_management_service,
        logging_broker,
        create_random_string,
        setup_orchestrations_pass_through,
        setup_direction_terminates):

    # given
    random_prompt = create_random_string()
    setup_orchestrations_pass_through()
    setup_direction_terminates(create_random_string())

    # when
    await run_management_service.process_prompt(random_prompt)

    # then
    narrated_outcomes = [
        outcome_call.args[0] for outcome_call in logging_broker.log_outcome.mock_calls
        if "done" in outcome_call.args[0]]

    assert len(narrated_outcomes) == 1
