# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The MCP JSON-RPC wire, read from the bytes the real broker sends (F-21): tools/list and
# tools/call as the protocol shapes them, ids that increase, schemas that survive untouched,
# arguments that arrive as an object, errors that surface, and a token asked for per request.

import http
import json
import urllib.request

import pytest

from restfulsense.exceptions import HttpRequestException
from standard_agents.brokers.mcps.http_mcp_broker import HttpMcpBroker
from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from tests.wire.scripted_server_handler import (
    ScriptedResponse,
    ScriptedServerHandler,
    header_of)


def create_broker(
        server: ScriptedServerHandler,
        bearer_token: str | None = None,
        api_key: str | None = None,
        bearer_token_provider=None) -> HttpMcpBroker:

    # The broker takes the composed opener, as StandardAgent hands it one over the host's
    # handler: no User-Agent of its own.
    opener = urllib.request.build_opener(server)
    opener.addheaders = []

    return HttpMcpBroker(
        endpoint_url="http://mcp.test/",
        relative_url="rpc",
        timeout_seconds=30,
        bearer_token=bearer_token,
        api_key=api_key,
        api_key_header="X-Api-Key",
        bearer_token_provider=bearer_token_provider,
        handler=opener)


def media_types_of(request: urllib.request.Request) -> list[str]:
    accept = header_of(request, "Accept") or ""

    return [media_type.split(";")[0].strip() for media_type in accept.split(",")]


async def test_should_post_tools_list_as_json_rpc_and_keep_schemas_whole():
    # given: a server listing one tool with a typed schema
    server = ScriptedServerHandler.answering(
        '{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"lookup",'
        + '"description":"looks up an account",'
        + '"inputSchema":{"type":"object","properties":{"account":{"type":"string"}},'
        + '"required":["account"]}}]}}')

    broker = create_broker(server, api_key="mcp-key")

    expected_tools = [
        McpTool(
            name="lookup",
            description="looks up an account",
            input_schema_json=(
                '{"type":"object","properties":{"account":{"type":"string"}},'
                + '"required":["account"]}'))
    ]

    # when
    actual_tools = await broker.list_tools()

    # then: the route, the credential header, the envelope, after the handshake
    request = server.requests[-1]
    assert request.full_url == "http://mcp.test/rpc"
    assert header_of(request, "X-Api-Key") == "mcp-key"

    body = json.loads(server.bodies[-1])
    assert body["jsonrpc"] == "2.0"
    assert body["method"] == "tools/list"
    assert body["id"] == 2

    # and the schema, verbatim (F-03)
    assert actual_tools == expected_tools


async def test_should_post_tools_call_with_arguments_as_an_object_and_increasing_ids():
    # given: a call after a list on the same broker
    server = ScriptedServerHandler(lambda request, body: (
        ScriptedServerHandler.json(
            http.HTTPStatus.OK,
            '{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}')
        if "tools/list" in body
        else ScriptedServerHandler.json(
            http.HTTPStatus.OK,
            '{"jsonrpc":"2.0","id":2,"result":{"content":'
            + '[{"type":"text","text":"owed: "},{"type":"text","text":"12"}]}}')))

    broker = create_broker(server, bearer_token="static-token")

    # when
    await broker.list_tools()
    actual_text = await broker.call("lookup", '{"account":"42","deep":{"n":1}}')

    # then: params as the protocol reads them, id advanced, text blocks joined
    call = json.loads(server.bodies[-1])
    assert call["method"] == "tools/call"
    assert call["id"] == 3
    assert call["params"]["name"] == "lookup"
    assert call["params"]["arguments"]["account"] == "42"
    assert call["params"]["arguments"]["deep"]["n"] == 1

    assert header_of(server.requests[-1], "Authorization") == "Bearer static-token"
    assert actual_text == "owed: 12"


async def test_should_throw_http_request_exception_on_a_json_rpc_error():
    # given: a well-formed 200 carrying a protocol error
    server = ScriptedServerHandler.answering(
        '{"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"unknown tool"}}')

    broker = create_broker(server)

    # when
    with pytest.raises(HttpRequestException) as raised:
        await broker.call("nope", "{}")

    # then: the server's own words, as a native exception for the foundation to localize
    assert raised.value.message == "unknown tool"


async def test_should_accept_json_and_an_event_stream_on_every_request():
    # given: a server free to answer either way, as the Streamable HTTP transport allows
    server = ScriptedServerHandler.answering('{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}')
    broker = create_broker(server)

    # when
    await broker.list_tools()

    # then: every request says it reads both
    for request in server.requests:
        media_types = media_types_of(request)
        assert "application/json" in media_types
        assert "text/event-stream" in media_types


async def test_should_read_the_reply_from_an_event_stream():
    # given: a server answering as the official SDKs do: an event stream, where a notification
    # may arrive before the response it carries
    server = ScriptedServerHandler.answering(
        "event: message\n"
        + 'data: {"jsonrpc":"2.0","method":"notifications/message",'
        + '"params":{"level":"info","data":"listing"}}\n'
        + "\n"
        + "event: message\n"
        + 'data: {"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"find_student",'
        + '"description":"Finds a student by their id.",'
        + '"inputSchema":{"type":"object","properties":{"id":{"type":"integer"}}}}]}}\n'
        + "\n",
        media_type="text/event-stream")

    broker = create_broker(server)

    expected_tools = [
        McpTool(
            name="find_student",
            description="Finds a student by their id.",
            input_schema_json='{"type":"object","properties":{"id":{"type":"integer"}}}')
    ]

    # when
    actual_tools = await broker.list_tools()

    # then: the response is found past the notification, the schema whole
    assert actual_tools == expected_tools


async def test_should_initialize_once_before_the_first_request():
    # given: a server that expects the lifecycle the protocol defines
    def respond(request, body):
        method = json.loads(body)["method"]

        if method == "initialize":
            return ScriptedServerHandler.json(
                http.HTTPStatus.OK,
                '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18",'
                + '"capabilities":{"tools":{}},'
                + '"serverInfo":{"name":"students","version":"1.0.0"}}}')

        if method == "notifications/initialized":
            return ScriptedResponse(http.HTTPStatus.ACCEPTED)

        return ScriptedServerHandler.json(
            http.HTTPStatus.OK,
            '{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}')

    server = ScriptedServerHandler(respond)
    broker = create_broker(server)

    # when
    await broker.list_tools()
    await broker.list_tools()

    # then: initialize, then the initialized notification, then the work; once only
    messages = [json.loads(body) for body in server.bodies]

    assert [message["method"] for message in messages] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
        "tools/list",
    ]

    initialize = messages[0]
    assert initialize.get("id") is not None
    assert initialize["params"]["protocolVersion"] == "2025-06-18"
    assert isinstance(initialize["params"]["capabilities"], dict)
    assert initialize["params"]["clientInfo"]["name"] == "Standard.Agents"
    assert messages[1].get("id") is None
