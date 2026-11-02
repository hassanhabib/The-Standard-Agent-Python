# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call

import pytest

from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.foundations.external_tools.exceptions import (
    ExternalToolDependencyException,
    ExternalToolDependencyValidationException,
    ExternalToolServiceException,
    InvalidExternalToolException)
from xeptions import Xeption


def _remote_discovery_exceptions() -> list[Xeption]:
    inner_exception = InvalidExternalToolException(message="Invalid external tool.")

    return [
        ExternalToolDependencyException(
            message="External tool dependency error occurred, contact support.",
            inner_exception=inner_exception),

        ExternalToolDependencyValidationException(
            message="External tool dependency validation error occurred.",
            inner_exception=inner_exception),

        ExternalToolServiceException(
            message="External tool service error occurred, contact support.",
            inner_exception=inner_exception)]


REMOTE_DISCOVERY_EXCEPTION_IDS = ["dependency", "dependency-validation", "service"]


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


@pytest.mark.parametrize(
    "remote_discovery_exception",
    _remote_discovery_exceptions(),
    ids=REMOTE_DISCOVERY_EXCEPTION_IDS)
async def test_should_retrieve_instructions_with_local_tools_only_when_remote_discovery_fails(
        remote_discovery_exception,
        retrieval_orchestration_service,
        skill_service,
        knowledge_service,
        external_tool_service,
        logging_broker,
        local_tool_catalog,
        create_random_string):
    """A server down at discovery hides only its own tools this turn and never fails the run.

    The foundation has already localized and logged the failure at the severity it earned, so
    the orchestration degrades to the local catalog.
    """
    # given
    random_route = create_random_string()
    input_route = random_route
    skills_with_marker = "Tools you may use:\n{{tools}}"
    expected_instructions = "Tools you may use:\n" + local_tool_catalog
    skill_service.retrieve_skills.return_value = skills_with_marker
    external_tool_service.retrieve_tools.side_effect = remote_discovery_exception

    # when
    actual_instructions = await retrieval_orchestration_service.retrieve_instructions(
        input_route)

    # then
    assert actual_instructions == expected_instructions
    assert skill_service.mock_calls == [call.retrieve_skills(input_route)]
    assert external_tool_service.mock_calls == [call.retrieve_tools()]
    assert knowledge_service.mock_calls == []
    assert logging_broker.mock_calls == []


async def test_should_not_retrieve_remote_tools_on_retrieve_instructions_when_the_marker_is_absent(
        retrieval_orchestration_service,
        skill_service,
        knowledge_service,
        external_tool_service,
        logging_broker,
        create_random_string):
    """An agent that never advertises never pays a discovery call: the marker is the opt-in."""
    # given
    random_route = create_random_string()
    input_route = random_route
    skills_without_marker = "You are a calculator agent."
    expected_instructions = skills_without_marker
    skill_service.retrieve_skills.return_value = skills_without_marker

    # when
    actual_instructions = await retrieval_orchestration_service.retrieve_instructions(
        input_route)

    # then
    assert actual_instructions == expected_instructions
    assert skill_service.mock_calls == [call.retrieve_skills(input_route)]
    assert external_tool_service.mock_calls == []
    assert knowledge_service.mock_calls == []
    assert logging_broker.mock_calls == []


async def test_should_retrieve_remote_tools(
        retrieval_orchestration_service,
        skill_service,
        knowledge_service,
        external_tool_service,
        logging_broker,
        create_random_string):
    """Every tool the servers declared, described or not, so the callers apply the opt-in."""
    # given
    random_tools = (
        McpTool(create_random_string(), create_random_string()),
        McpTool(create_random_string(), ""))

    expected_tools = random_tools
    external_tool_service.retrieve_tools.return_value = random_tools

    # when
    actual_tools = await retrieval_orchestration_service.retrieve_remote_tools()

    # then
    assert actual_tools == expected_tools
    assert external_tool_service.mock_calls == [call.retrieve_tools()]
    assert skill_service.mock_calls == []
    assert knowledge_service.mock_calls == []
    assert logging_broker.mock_calls == []


@pytest.mark.parametrize(
    "remote_discovery_exception",
    _remote_discovery_exceptions(),
    ids=REMOTE_DISCOVERY_EXCEPTION_IDS)
async def test_should_retrieve_no_remote_tools_when_discovery_fails(
        remote_discovery_exception,
        retrieval_orchestration_service,
        skill_service,
        knowledge_service,
        external_tool_service,
        logging_broker):
    """A server that cannot be asked offers nothing this turn; the foundation logged why."""
    # given
    external_tool_service.retrieve_tools.side_effect = remote_discovery_exception

    # when
    actual_tools = await retrieval_orchestration_service.retrieve_remote_tools()

    # then
    assert len(actual_tools) == 0
    assert external_tool_service.mock_calls == [call.retrieve_tools()]
    assert skill_service.mock_calls == []
    assert knowledge_service.mock_calls == []
    assert logging_broker.mock_calls == []
