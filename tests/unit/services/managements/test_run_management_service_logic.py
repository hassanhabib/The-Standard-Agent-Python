# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------


async def test_should_process_prompt(
        run_management_service,
        create_random_string,
        setup_orchestrations_pass_through,
        setup_direction_terminates):

    # given
    random_prompt = create_random_string()
    expected_result = create_random_string()

    setup_orchestrations_pass_through()
    setup_direction_terminates(expected_result)

    # when
    actual_result = await run_management_service.process_prompt(random_prompt)

    # then
    assert actual_result == expected_result
