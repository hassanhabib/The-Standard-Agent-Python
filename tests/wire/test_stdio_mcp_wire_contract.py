# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The MCP stdio wire, read from the lines the real broker writes: one JSON-RPC message per line,
# the lifecycle first, notifications skipped, a server's own requests answered.

import json

import pytest

from restfulsense.exceptions import HttpRequestException
from standard_agents.brokers.mcps.stdio_mcp_broker import StdioMcpBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from tests.wire.scripted_stdio_server import ScriptedStdioServer

INITIALIZE_RESULT = (
    '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18",'
    + '"capabilities":{"tools":{}},"serverInfo":{"name":"students","version":"1.0.0"}}}')


def answer(message, *lines: str) -> list[str]:
    return [line.replace("{id}", json.dumps(message["id"])) for line in lines]


def answer_initialize(message) -> list[str]:
    return answer(message, INITIALIZE_RESULT.replace('"id":1', '"id":{id}'))


def create_broker(server: ScriptedStdioServer) -> StdioMcpBroker:
    return StdioMcpBroker(server.output, server.input, timeout_seconds=30)


async def test_should_initialize_over_standard_input_before_the_first_request():
    # given: a server that expects the lifecycle before anything else
    def respond(message):
        method = message["method"]

        if method == "initialize":
            return answer_initialize(message)

        if method == "notifications/initialized":
            return []

        return answer(
            message,
            '{"jsonrpc":"2.0","id":{id},"result":{"tools":[{"name":"find_student",'
            + '"description":"Finds a student by their id.",'
            + '"inputSchema":{"type":"object","properties":{"id":{"type":"integer"}}}}]}}')

    server = ScriptedStdioServer(respond)
    broker = create_broker(server)

    expected_tools = [
        McpTool(
            name="find_student",
            description="Finds a student by their id.",
            input_schema_json='{"type":"object","properties":{"id":{"type":"integer"}}}')
    ]

    # when
    actual_tools = await broker.list_tools()

    # then: initialize, the initialized notification, then the listing; one message per line
    assert [json.loads(line)["method"] for line in server.lines] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
    ]

    assert all("\n" not in line for line in server.lines)
    assert actual_tools == expected_tools


async def test_should_skip_what_is_not_its_answer_and_answer_the_pings_of_the_server():
    # given: a server that, before answering, logs a line to its output, sends a notification,
    # and pings the client with an id that collides with the client's own
    def respond(message):
        method = message.get("method")

        if method == "initialize":
            return answer_initialize(message)

        if method == "tools/list":
            return answer(
                message,
                "server ready on stdio",
                '{"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info"}}',
                '{"jsonrpc":"2.0","id":{id},"method":"ping"}',
                '{"jsonrpc":"2.0","id":{id},"result":{"tools":[{"name":"find_student"}]}}')

        return []

    server = ScriptedStdioServer(respond)
    broker = create_broker(server)

    # when
    actual_tools = await broker.list_tools()

    # then: the answer is found past the noise, and the ping was answered
    assert [tool.name for tool in actual_tools] == ["find_student"]

    pong = json.loads(server.lines[-1])
    assert pong["id"] == 2
    assert isinstance(pong["result"], dict)
    assert pong.get("method") is None


async def test_should_call_a_tool_with_its_arguments_and_read_every_kind_of_content():
    # given: a tool that answers with text, an embedded resource and a link
    def respond(message):
        method = message.get("method")

        if method == "initialize":
            return answer_initialize(message)

        if method == "tools/call":
            return answer(
                message,
                '{"jsonrpc":"2.0","id":{id},"result":{"content":['
                + '{"type":"text","text":"student: "},'
                + '{"type":"resource","resource":{"uri":"students://1","text":"Hassan"}},'
                + '{"type":"resource_link","uri":"file:///1.json","name":"record"}]}}')

        return []

    server = ScriptedStdioServer(respond)
    broker = create_broker(server)

    # when
    actual_text = await broker.call("find_student", '{"id":1,"deep":{"n":2}}')

    # then: the arguments travel as the object the model wrote, and nothing returned is dropped
    call = json.loads(server.lines[-1])
    assert call["method"] == "tools/call"
    assert call["params"]["name"] == "find_student"
    assert call["params"]["arguments"]["id"] == 1
    assert call["params"]["arguments"]["deep"]["n"] == 2

    assert actual_text == "student: Hassan[resource_link record: file:///1.json]"
