# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.tools.remember_tool import RememberTool


async def test_should_write_to_memory_on_execute():
    # given
    fact = "Hassan works on PeerLLM"
    remembered = []

    async def remember(memory):
        remembered.append(memory)

    remember_tool = RememberTool(remember)

    # when
    actual_result = await remember_tool.execute(fact)

    # then
    assert fact in actual_result
    assert remembered == [fact]
