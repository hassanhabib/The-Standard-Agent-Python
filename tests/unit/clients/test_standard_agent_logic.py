# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------


async def test_should_compose_and_process_prompt(create_fully_stubbed_agent):
    # given
    agent = create_fully_stubbed_agent("FINAL: 42")

    # when
    actual_result = await agent.process_prompt(prompt="what is the answer?")

    # then
    assert actual_result == "42"
