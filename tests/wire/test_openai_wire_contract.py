# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Found in the 2026-09-04 principal review (F-21): the native OpenAI-compatible broker was only
# ever exercised through scripted doubles, so the route, the headers, the request shape, the
# response variants and the failure modes of the real wire could drift unseen. These run the
# real broker against a scripted protocol server and read the bytes.

import http
import json

import pytest

from restfulsense.exceptions import HttpRequestException
from standard_agents.brokers.generators.openai_generator_broker_v1 import OpenAiGeneratorBrokerV1
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    MessageRole,
    ModelToolCall,
    ToolDefinition)
from tests.wire.scripted_server_handler import ScriptedServerHandler, header_of

BASE_URL = "http://provider.test/v1/"

CONVERSATION = (
    ConversationMessage(role=MessageRole.SYSTEM, content="be brief"),
    ConversationMessage(role=MessageRole.USER, content="what is owed on 42?"),

    ConversationMessage(
        role=MessageRole.ASSISTANT,
        tool_calls=(ModelToolCall("call_1", "lookup", '{"account":"42"}'),)),

    ConversationMessage(role=MessageRole.TOOL, content="owed: 12", tool_call_id="call_1"),
)

TOOLS = (
    ToolDefinition(
        name="lookup",
        description="looks up an account",
        parameters_json='{"type":"object","properties":{"account":{"type":"string"}}}'),
)


def create_broker(
        server: ScriptedServerHandler,
        timeout_seconds: int = 30) -> OpenAiGeneratorBrokerV1:

    return OpenAiGeneratorBrokerV1(
        BASE_URL,
        "key-1",
        "model-1",
        temperature=0.2,
        max_tokens=64,
        timeout_seconds=timeout_seconds,
        handler=server)


async def test_should_post_a_chat_completion_in_the_open_ai_shape():
    # given: a server answering with a tool call and usage
    server = ScriptedServerHandler.answering(
        '{"choices":[{"message":{"role":"assistant","content":null,'
        + '"tool_calls":[{"id":"call_2","type":"function",'
        + '"function":{"name":"lookup","arguments":"{\\"account\\":\\"7\\"}"}}]}}],'
        + '"usage":{"prompt_tokens":21,"completion_tokens":8}}')

    broker = create_broker(server)

    expected_result = GenerationResult(
        content="",
        tool_calls=(ModelToolCall("call_2", "lookup", '{"account":"7"}'),),
        prompt_tokens=21,
        completion_tokens=8)

    # when
    actual_result = await broker.generate(CONVERSATION, TOOLS)

    # then: the route, the credential, the media type
    [request] = server.requests
    assert request.get_method() == "POST"
    assert request.full_url == "http://provider.test/v1/chat/completions"
    assert header_of(request, "Authorization") == "Bearer key-1"
    assert header_of(request, "Content-Type").split(";")[0] == "application/json"

    # and the request body, as the provider reads it
    body = json.loads(server.bodies[0])
    assert body["model"] == "model-1"
    assert body["temperature"] == 0.2
    assert body["max_tokens"] == 64

    messages = body["messages"]
    assert len(messages) == 4
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[2]["tool_calls"][0]["id"] == "call_1"
    assert messages[2]["tool_calls"][0]["type"] == "function"
    assert messages[2]["tool_calls"][0]["function"]["arguments"] == '{"account":"42"}'
    assert messages[3]["role"] == "tool"
    assert messages[3]["tool_call_id"] == "call_1"

    tool = body["tools"][0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "lookup"
    assert tool["function"]["parameters"]["type"] == "object"

    # and the response, read back whole
    assert actual_result == expected_result


async def test_should_not_advertise_an_empty_tool_list():
    # given: no tools; some providers treat "tools": [] as a different request
    server = ScriptedServerHandler.answering(
        '{"choices":[{"message":{"role":"assistant","content":"12"}}]}')

    broker = create_broker(server)

    # when
    actual_result = await broker.generate(CONVERSATION, tools=())

    # then
    body = json.loads(server.bodies[0])
    assert "tools" not in body
    assert actual_result.content == "12"


async def test_should_read_an_answer_without_usage_as_zero_tokens():
    # given: a partial answer: no usage block, no tool calls, content only
    server = ScriptedServerHandler.answering(
        '{"choices":[{"message":{"role":"assistant","content":"12"}}]}')

    broker = create_broker(server)
    expected_result = GenerationResult(content="12")

    # when
    actual_result = await broker.generate(CONVERSATION, TOOLS)

    # then: reported, not estimated: zero says "the provider did not say"
    assert actual_result == expected_result


@pytest.mark.parametrize("status_code", [
    http.HTTPStatus.TOO_MANY_REQUESTS,
    http.HTTPStatus.INTERNAL_SERVER_ERROR,
    http.HTTPStatus.UNAUTHORIZED,
])
async def test_should_throw_http_request_exception_on_a_failed_status(status_code):
    # given: the provider refusing, throttling or failing
    server = ScriptedServerHandler.answering_with(status_code, '{"error":{"message":"no"}}')
    broker = create_broker(server)

    # when
    with pytest.raises(HttpRequestException) as raised:
        await broker.generate(CONVERSATION, TOOLS)

    # then: a native exception, for the foundation above to localize
    assert raised.value.status_code == status_code


async def test_should_throw_json_exception_on_a_malformed_body():
    # given: a 200 that is not JSON (a proxy's HTML page, a truncated stream)
    server = ScriptedServerHandler.answering("<html>bad gateway</html>", media_type="text/html")
    broker = create_broker(server)

    # when, then
    with pytest.raises(json.JSONDecodeError):
        await broker.generate(CONVERSATION, TOOLS)
