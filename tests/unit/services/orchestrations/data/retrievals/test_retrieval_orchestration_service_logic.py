# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

from standard_agents.models.brokers.mcps.mcp_tool import McpTool


async def test_should_retrieve_instructions_with_remote_tools_when_the_marker_is_present(
        retrieval_orchestration_service,
        skill_service,
        knowledge_service,
        external_tool_service,
        logging_broker,
        local_tool_catalog,
        create_random_string):
    """Remote tools join the catalog under the same opt-in as local ones (SPEC.md 6.1).

    A description is what advertises a tool, so an undescribed remote tool stays callable but
    unlisted, and the schema the server declared reaches the catalog line.
    """
    # given
    random_route = create_random_string()
    input_route = random_route
    skills_with_marker = "Tools you may use:\n{{tools}}"
    weather_schema = '{"type":"object","properties":{"city":{"type":"string"}}}'

    remote_tools = (
        McpTool("weather", "answers weather questions", weather_schema),
        McpTool("undocumented", ""))

    expected_instructions = (
        "Tools you may use:\n"
        + local_tool_catalog + "\n"
        + "- weather \u2014 answers weather questions parameters: " + weather_schema)

    skill_service.retrieve_skills.return_value = skills_with_marker
    external_tool_service.retrieve_tools.return_value = remote_tools

    # when
    actual_instructions = await retrieval_orchestration_service.retrieve_instructions(
        input_route)

    # then
    assert actual_instructions == expected_instructions
    assert skill_service.mock_calls == [call.retrieve_skills(input_route)]
    assert external_tool_service.mock_calls == [call.retrieve_tools()]
    assert knowledge_service.mock_calls == []
    assert logging_broker.mock_calls == []
