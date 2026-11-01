# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Discovery (tools/list) already routes calls; these tests make it advertise too. A remote tool
# with a description belongs in the {{tools}} catalog beside the local ones: the same opt-in rule
# (a description is the advertisement), the same catalog line, and best-effort: a server down at
# advertisement time hides only its own tools and never fails the turn.

from restfulsense import HttpRequestException
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.standard_agent import StandardAgent


async def select_persona():
    return [Skill(name="persona", content="Your tools:\n{{tools}}")]


async def test_should_advertise_described_mcp_tools_in_the_catalog(
        empty_memory_broker,
        empty_knowledge_broker,
        create_mcp_broker):

    # given: a server offering one described and one undescribed tool.
    server = create_mcp_broker()

    server.list_tools.return_value = [
        McpTool("weather", "answers weather questions"),
        McpTool("undocumented", ""),
    ]

    captured_system_prompts = []

    async def brain(system_prompt, user_prompt):
        captured_system_prompts.append(system_prompt)

        return "FINAL: done"

    agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_skills(select_persona)
        .use_mcp(server)
        .on_brain(brain))

    # when
    await agent.process_prompt("hello")

    # then: described remote tools advertise; the description opt-in holds for them too.
    assert "weather \u2014 answers weather questions" in captured_system_prompts[-1]
    assert "undocumented" not in captured_system_prompts[-1]


async def test_should_still_answer_when_advertisement_discovery_fails(
        empty_memory_broker,
        empty_knowledge_broker,
        create_mcp_broker):

    # given: a server that cannot even list its tools.
    server = create_mcp_broker()
    server.list_tools.side_effect = HttpRequestException("server is down")

    async def brain(system_prompt, user_prompt):
        return "FINAL: 42"

    agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_skills(select_persona)
        .use_mcp(server)
        .on_brain(brain))

    # when
    answer = await agent.process_prompt("hello")

    # then: advertisement is best-effort; a down server never fails the turn.
    assert answer == "42"
