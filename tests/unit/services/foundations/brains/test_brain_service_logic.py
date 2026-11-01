# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call


async def test_should_generate(
        brain_service, generator_broker, logging_broker, create_random_string):

    # given
    random_system_prompt = create_random_string()
    random_user_prompt = create_random_string()
    random_reply = create_random_string()
    input_system_prompt = random_system_prompt
    input_user_prompt = random_user_prompt
    expected_reply = random_reply
    generator_broker.generate.return_value = random_reply

    # when
    actual_reply = await brain_service.generate(input_system_prompt, input_user_prompt)

    # then
    assert actual_reply == expected_reply

    assert generator_broker.mock_calls == [
        call.generate(input_system_prompt, input_user_prompt)]

    assert logging_broker.mock_calls == []


async def test_should_pass_prompts_through_unaltered_on_generate(
        brain_service, generator_broker, logging_broker, create_random_string):

    # given
    system_prompt_with_formatting = "  You are an agent.\n\nRules:\n- be terse  "
    user_prompt_with_formatting = "  what is 1+1?  "
    random_reply = create_random_string()
    expected_reply = random_reply
    generator_broker.generate.return_value = random_reply

    # when
    actual_reply = await brain_service.generate(
        system_prompt_with_formatting,
        user_prompt_with_formatting)

    # then
    assert actual_reply == expected_reply

    assert generator_broker.mock_calls == [
        call.generate(system_prompt_with_formatting, user_prompt_with_formatting)]

    assert logging_broker.mock_calls == []
