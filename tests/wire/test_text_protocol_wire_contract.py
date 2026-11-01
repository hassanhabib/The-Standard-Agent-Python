# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The text-protocol brain over the OpenAI-compatible wire, batched and streamed, read from the
# bytes the real broker sends and parsed from the bytes a server sends back (F-21). The stream
# is where wire contracts drift most: frame boundaries, comments, blank lines, the sentinel.

import json

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
