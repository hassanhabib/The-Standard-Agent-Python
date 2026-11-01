# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The Anthropic Messages wire, read from the bytes the real broker sends (F-21): the route, the
# version pin, the top-level system, tool_use and tool_result blocks, and the usage names.

import http
import json

import pytest

from restfulsense.exceptions import HttpRequestException
from standard_agents.brokers.generators.anthropic_generator_broker_v1 import (
    AnthropicGeneratorBrokerV1)
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    MessageRole,
    ModelToolCall,
    ToolDefinition)
from tests.wire.scripted_server_handler import ScriptedServerHandler, header_of

CONVERSATION = (
    ConversationMessage(role=MessageRole.SYSTEM, content="be brief"),
    ConversationMessage(role=MessageRole.USER, content="what is owed on 42?"),

    ConversationMessage(
        role=MessageRole.ASSISTANT,
        tool_calls=(ModelToolCall("toolu_1", "lookup", '{"account":"42"}'),)),

    ConversationMessage(role=MessageRole.TOOL, content="owed: 12", tool_call_id="toolu_1"),
)

TOOLS = (
    ToolDefinition(
        name="lookup",
        description="looks up an account",
        parameters_json='{"type":"object","properties":{"account":{"type":"string"}}}'),
)


def create_broker(server: ScriptedServerHandler) -> AnthropicGeneratorBrokerV1:
    return AnthropicGeneratorBrokerV1(
        api_key="key-1",
        model="claude-x",
        temperature=0.2,
        max_tokens=64,
        timeout_seconds=30,
        api_url="http://anthropic.test/",
        handler=server)


async def test_should_post_messages_in_the_anthropic_shape():
    # given: a server answering with a text block, a tool_use block and usage
    server = ScriptedServerHandler.answering(
        '{"content":[{"type":"text","text":"checking "},'
        + '{"type":"tool_use","id":"toolu_2","name":"lookup","input":{"account":"7"}}],'
        + '"usage":{"input_tokens":21,"output_tokens":8}}')

    broker = create_broker(server)

    expected_result = GenerationResult(
        content="checking ",
        tool_calls=(ModelToolCall("toolu_2", "lookup", '{"account":"7"}'),),
        prompt_tokens=21,
        completion_tokens=8)

    # when
    actual_result = await broker.generate(CONVERSATION, TOOLS)

    # then: the route and the two headers the API refuses a request without
    [request] = server.requests
    assert request.full_url == "http://anthropic.test/v1/messages"
    assert header_of(request, "x-api-key") == "key-1"
    assert header_of(request, "anthropic-version") == "2023-06-01"

    # and the body: system at the top level, never as a message role
    body = json.loads(server.bodies[0])
    assert body["model"] == "claude-x"
    assert body["max_tokens"] == 64
    assert body["system"] == "be brief"

    roles = [message["role"] for message in body["messages"]]
    assert "system" not in roles
    assert "tool" not in roles

    # the assistant's call as a tool_use block, the answer as a tool_result block in a USER turn
    rendered = server.bodies[0]
    assert '"type":"tool_use"' in rendered and '"id":"toolu_1"' in rendered
    assert '"type":"tool_result"' in rendered and '"tool_use_id":"toolu_1"' in rendered

    tool = body["tools"][0]
    assert tool["name"] == "lookup"
    assert tool["input_schema"]["type"] == "object"

    # and the response, read back whole
    assert actual_result == expected_result


@pytest.mark.parametrize("status_code", [
    http.HTTPStatus.TOO_MANY_REQUESTS,
    http.HTTPStatus.INTERNAL_SERVER_ERROR,
])
async def test_should_throw_http_request_exception_on_a_failed_status(status_code):
    # given
    server = ScriptedServerHandler.answering_with(
        status_code,
        '{"type":"error","error":{"type":"rate_limit_error"}}')

    broker = create_broker(server)

    # when
    with pytest.raises(HttpRequestException) as raised:
        await broker.generate(CONVERSATION, TOOLS)

    # then
    assert raised.value.status_code == status_code


async def test_should_read_an_answer_with_no_blocks_as_empty():
    # given: a stop with nothing in it
    server = ScriptedServerHandler.answering('{"content":[],"stop_reason":"end_turn"}')
    broker = create_broker(server)
    expected_result = GenerationResult()

    # when
    actual_result = await broker.generate(CONVERSATION, TOOLS)

    # then
    assert actual_result == expected_result


# No C# twin: DefaultRequestHeaders.Add("x-api-key", null) adds the header with an empty value,
# so a broker built without a key still sends x-api-key, empty, and lets the API refuse it.
async def test_should_send_an_empty_api_key_header_when_built_without_an_api_key():
    # given
    server = ScriptedServerHandler.answering('{"content":[]}')

    broker = AnthropicGeneratorBrokerV1(
        api_key=None,
        model="claude-x",
        api_url="http://anthropic.test/",
        handler=server)

    # when
    await broker.generate(CONVERSATION, TOOLS)

    # then
    assert header_of(server.requests[0], "x-api-key") == ""
