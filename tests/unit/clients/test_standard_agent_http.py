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


async def test_should_route_the_native_brain_through_the_supplied_http_handler(bare_shell):
    # given: the same handler under the native tool-calling brain, supplied AFTER the brain,
    # because a seam that only works in one order is a trap
    handler = RecordingHandler(NATIVE_CHAT_COMPLETION)

    agent = (bare_shell
        .native_brain("http://brain.test/v1/", "key-1", "model-1")
        .http(lambda: handler))

    # when
    answer = await agent.process_prompt("2+2")

    # then
    assert answer == "4"
    assert len(handler.requests) == 1
    assert handler.requests[0].full_url == "http://brain.test/v1/chat/completions"
    assert header_of(handler.requests[0], "Authorization") == "Bearer key-1"


async def test_should_route_mcp_discovery_through_the_supplied_http_handler(bare_shell):
    # given: an MCP server registered before the handler, discovered on the run
    handler = RecordingHandler(EMPTY_TOOL_LIST)

    async def brain(system_prompt, user_prompt):
        return "FINAL: done"

    agent = (bare_shell
        .on_brain(brain)
        .mcp("http://mcp.test/", api_key="mcp-key")
        .http(lambda: handler))

    # when
    await agent.process_prompt("anything")

    # then: the handshake and discovery went out through the host's handler, credentials intact
    assert handler.requests

    for request in handler.requests:
        assert request.full_url == "http://mcp.test/"
        assert header_of(request, "X-Api-Key") == "mcp-key"

    assert '"initialize"' in handler.bodies[0]
    assert "tools/list" in handler.bodies[-1]
