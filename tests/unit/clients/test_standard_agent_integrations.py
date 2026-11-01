# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The integration rule: what the agent connects TO accumulates, never replaces. Tools always did;
# these tests hold MCP servers and skill sources to the same rule: a second registration must not
# silently unplug the first.

from unittest.mock import ANY, call

from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.standard_agent import StandardAgent


async def test_should_route_across_multiple_mcp_servers_by_tool_name(
        empty_memory_broker,
        empty_knowledge_broker,
        create_mcp_broker):

    # given: two servers, each owning one tool; the FIRST registered owns 'alpha'.
    first_server = create_mcp_broker()
    first_server.list_tools.return_value = [McpTool("alpha", "first server's tool")]
    first_server.call.return_value = "42 from the first server"
    second_server = create_mcp_broker()
    second_server.list_tools.return_value = [McpTool("beta", "second server's tool")]
    replies = iter(["ACTION: alpha: ping", "FINAL: done"])

    async def brain(system_prompt, user_prompt):
        return next(replies)

    agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .use_mcp(first_server)
        .use_mcp(second_server)
        .on_brain(brain))

    # when
    await agent.process_prompt("use alpha")

    # then: the call reached the server that owns the name, not merely the last one added.
    assert [recorded for recorded in first_server.mock_calls if recorded[0] == "call"] == [
        call.call("alpha", ANY)]

    assert second_server.call.call_count == 0
