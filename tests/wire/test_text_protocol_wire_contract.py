# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The text-protocol brain over the OpenAI-compatible wire, batched and streamed, read from the
# bytes the real broker sends and parsed from the bytes a server sends back (F-21). The stream
# is where wire contracts drift most: frame boundaries, comments, blank lines, the sentinel.

import http
import json

import pytest

from restfulsense.exceptions import HttpRequestException, HttpResponseTooManyRequestsException
from standard_agents.brokers.generators.openai_generator_broker import OpenAiGeneratorBroker
from tests.wire.scripted_server_handler import ScriptedServerHandler, header_of

BASE_URL = "http://provider.test/v1/"


def create_broker(server: ScriptedServerHandler) -> OpenAiGeneratorBroker:
    return OpenAiGeneratorBroker(
        BASE_URL,
        "key-1",
        "model-1",
        temperature=0.2,
        max_tokens=64,
        timeout_seconds=30,
        handler=server)


async def test_should_post_a_chat_completion_and_read_the_answer():
    # given
    server = ScriptedServerHandler.answering(
        '{"choices":[{"message":{"role":"assistant","content":"FINAL: 12"}}]}')

    broker = create_broker(server)

    # when
    actual_answer = await broker.generate("be brief", "what is owed?")

    # then: the route, the credential, and the two-message body
    [request] = server.requests
    assert request.full_url == "http://provider.test/v1/chat/completions"
    assert header_of(request, "Authorization") == "Bearer key-1"

    body = json.loads(server.bodies[0])
    assert body["model"] == "model-1"
    assert body.get("stream") is not True

    messages = body["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "be brief"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "what is owed?"

    assert actual_answer == "FINAL: 12"


async def test_should_stream_data_frames_until_the_done_sentinel():
    # given: an SSE body with a comment, a non-data field, blank lines, an empty delta, the
    # sentinel, and a frame after the sentinel that must never be read
    server = ScriptedServerHandler.answering(
        ": keep-alive\n"
        + "event: message\n"
        + 'data: {"choices":[{"delta":{"content":"FIN"}}]}\n\n'
        + 'data: {"choices":[{"delta":{"content":"AL: "}}]}\n\n'
        + 'data: {"choices":[{"delta":{}}]}\n\n'
        + 'data: {"choices":[{"delta":{"content":"12"}}]}\n\n'
        + "data: [DONE]\n\n"
        + 'data: {"choices":[{"delta":{"content":"NOT READ"}}]}\n\n',
        media_type="text/event-stream")

    broker = create_broker(server)

    # when
    streamed = [chunk async for chunk in broker.generate_stream("be brief", "what is owed?")]

    # then: the request asked to stream; only content deltas came out, in order, then stop
    body = json.loads(server.bodies[0])
    assert body["stream"] is True
    assert streamed == ["FIN", "AL: ", "12"]


async def test_should_end_the_stream_when_the_connection_ends_without_a_sentinel():
    # given: a provider that drops the connection mid-stream
    server = ScriptedServerHandler.answering(
        'data: {"choices":[{"delta":{"content":"FINAL: 1"}}]}\n\n'
        + 'data: {"choices":[{"delta":{"content":"2"}}]}\n\n',
        media_type="text/event-stream")

    broker = create_broker(server)

    # when
    streamed = [chunk async for chunk in broker.generate_stream("be brief", "what is owed?")]

    # then: what arrived is delivered; the enumeration completes rather than hangs
    assert streamed == ["FINAL: 1", "2"]


async def test_should_throw_on_a_throttled_stream_before_reading_any_frame():
    # given
    server = ScriptedServerHandler.answering_with(
        http.HTTPStatus.TOO_MANY_REQUESTS,
        '{"error":{"message":"slow down"}}')

    broker = create_broker(server)

    # when
    async def stream():
        async for _ in broker.generate_stream("be brief", "what is owed?"):
            pass

    # then
    with pytest.raises(HttpRequestException) as raised:
        await stream()

    assert raised.value.status_code == http.HTTPStatus.TOO_MANY_REQUESTS


async def test_should_throw_the_typed_rest_exception_on_a_throttled_completion():
    # given: the batched door rides RESTFulSense, which types the status
    server = ScriptedServerHandler.answering_with(
        http.HTTPStatus.TOO_MANY_REQUESTS,
        '{"error":{"message":"slow down"}}')

    broker = create_broker(server)

    # when, then
    with pytest.raises(HttpResponseTooManyRequestsException):
        await broker.generate("be brief", "what is owed?")
