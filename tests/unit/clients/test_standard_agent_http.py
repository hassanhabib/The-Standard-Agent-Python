# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Found in the 2026-09-04 principal review (F-23): every HTTP broker built its own client and
# nothing could reach it, so a host could not put its own handler chain (a proxy, a certificate,
# an observer) under the agent's traffic. http(...) is the seam: the host supplies the handler,
# every HTTP broker rides it, and ownership is explicit: the handler is the host's.

import io
import urllib.request
import urllib.response
from email.message import Message

import pytest

from standard_agents.standard_agent import StandardAgent

CHAT_COMPLETION = (
    '{"choices":[{"message":{"role":"assistant","content":"FINAL: 4"}}],'
    + '"usage":{"prompt_tokens":1,"completion_tokens":1}}')

# The native protocol carries the answer as the content itself; no FINAL: marker.
NATIVE_CHAT_COMPLETION = (
    '{"choices":[{"message":{"role":"assistant","content":"4"}}],'
    + '"usage":{"prompt_tokens":1,"completion_tokens":1}}')

EMPTY_TOOL_LIST = '{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}'


class RecordingHandler(urllib.request.HTTPHandler):
    """Records what went out and answers with one scripted body: the test's stand-in for the
    handler chain a host would supply."""

    def __init__(self, body: str) -> None:
        super().__init__()
        self.body = body
        self.requests: list[urllib.request.Request] = []
        self.bodies: list[str] = []

    def http_open(self, request: urllib.request.Request):
        self.requests.append(request)
        self.bodies.append((request.data or b"").decode("utf-8"))
        headers = Message()
        headers["Content-Type"] = "application/json; charset=utf-8"

        response = urllib.response.addinfourl(
            io.BytesIO(self.body.encode("utf-8")),
            headers,
            request.full_url,
            200)

        response.msg = "OK"

        return response


def header_of(request: urllib.request.Request, name: str) -> str | None:
    return {key.lower(): value for key, value in request.header_items()}.get(name.lower())


@pytest.fixture
def bare_shell(create_skill_broker, empty_memory_broker, empty_knowledge_broker):
    return (StandardAgent()
        .use_skills(create_skill_broker())
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker))


# OpenAiGeneratorBroker.generate posts through RESTFulApiFactoryClient, which builds its own
# opener and never sees the host's handler (only generate_stream rides it). A broker defect, not
# the agent's: the agent hands the handler over, and this turns red the day the broker uses it.
@pytest.mark.xfail(
    reason="OpenAiGeneratorBroker.generate ignores the host's handler (restfulsense client)",
    strict=True)
async def test_should_route_the_brain_through_the_supplied_http_handler(bare_shell):
    # given: a host-owned handler under the text-protocol brain
    handler = RecordingHandler(CHAT_COMPLETION)

    agent = (bare_shell
        .http(lambda: handler)
        .brain("http://brain.test/v1/", "key-1", "model-1"))

    # when
    answer = await agent.process_prompt("2+2")

    # then: the request left through the host's handler, at the route the base composes to
    assert answer == "4"
    assert len(handler.requests) == 1
    assert handler.requests[0].full_url == "http://brain.test/v1/chat/completions"
    assert header_of(handler.requests[0], "Authorization") == "Bearer key-1"
