# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The real host, stood up on a free port, and a real HTTP client to speak to it.

The C# host tests stand the host up in memory through WebApplicationFactory<Program>; these
compose it through create_host, the same composition `python -m standard_agents.host` runs, bind
it to 127.0.0.1:0 and speak HTTP/1.1 to it with http.client. The agent behind the door is a
double unless a test composes a real one: the host is the unit here, and the loop has its own
suite.
"""

from __future__ import annotations

import asyncio
import dataclasses
import http.client
import json
import urllib.parse
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import create_autospec

import pytest

from standard_agents.agent import Agent
from standard_agents.host.program import create_host
from standard_agents.models.brokers.generators.v1.conversation import ToolDefinition
from standard_agents.models.brokers.sessions.agent_session import AgentTurn
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: http.client.HTTPMessage
    text: str

    @property
    def media_type(self) -> str | None:
        content_type = self.headers.get("Content-Type")

        return content_type.split(";")[0].strip() if content_type else None

    def json(self):
        return json.loads(self.text)


class HttpClient:
    """A plain HTTP/1.1 client over http.client, run off the event loop the host serves on."""

    def __init__(self, base_url: str) -> None:
        self.base_url = urllib.parse.urlsplit(base_url)
        self.headers: dict[str, str] = {}

    async def get(self, path: str) -> HttpResponse:
        return await self.send("GET", path)

    async def post_json(self, path: str, document: object) -> HttpResponse:
        return await self.post(path, json.dumps(document), "application/json; charset=utf-8")

    async def post(self, path: str, body: str, content_type: str) -> HttpResponse:
        return await self.send("POST", path, body.encode("utf-8"), {"Content-Type": content_type})

    async def send(
            self,
            method: str,
            path: str,
            body: bytes | None = None,
            headers: dict[str, str] | None = None) -> HttpResponse:

        return await asyncio.to_thread(
            self._send, method, path, body, {**self.headers, **(headers or {})})

    def _send(self, method, path, body, headers) -> HttpResponse:
        connection = http.client.HTTPConnection(
            self.base_url.hostname, self.base_url.port, timeout=10)

        try:
            connection.request(method, "/" + path.lstrip("/"), body=body, headers=headers)
            response = connection.getresponse()
            text = response.read().decode("utf-8")

            return HttpResponse(response.status, response.headers, text)
        finally:
            connection.close()


@pytest.fixture
def agent():
    return create_autospec(Agent, instance=True)


@pytest.fixture
def serve_host(agent):
    """Stand the host up with these settings, the agent double behind it unless told otherwise.

    settings are configuration keys, as UseSetting gives them to the C# host; agent_factory is
    the agent registration, handed the host's principal resolver; authenticate is the
    authentication scheme.
    """

    @asynccontextmanager
    async def serve(settings=None, *, agent_factory=None, authenticate=None):
        configuration = {"urls": "http://127.0.0.1:0", **(settings or {})}

        host = create_host(
            configuration,
            agent_factory=agent_factory or (lambda principals: agent),
            authenticate=authenticate)

        async with host:
            yield HttpClient(host.urls[0])

    return serve


@pytest.fixture
def v1_document():
    """An AgentRunRequestV1 as ASP.NET's web serializer writes it: camelCase, nulls included."""

    def create(**fields) -> dict:
        document = {
            "prompt": "",
            "sessionId": "",
            "history": [],
            "toolExchanges": [],
            "callerTools": [],
            "responseSchemaJson": None,
            "temperature": None,
            "maxTokens": None,
            "seed": None,
            "stop": [],
            "providerOptionsJson": None,
            "citeKnowledge": None,
        }

        document.update(fields)

        return document

    return create


@pytest.fixture
def full_request_document(v1_document) -> dict:
    return v1_document(
        prompt="wire the money",
        sessionId="trip-3",
        history=[{"prompt": "hello", "answer": "hi", "exchanges": []}],

        toolExchanges=[{
            "callId": "call-1",
            "toolName": "lookup",
            "argumentsJson": '{"account":"42"}',
            "result": "owed: 12",
        }],

        callerTools=[{
            "name": "lookup",
            "description": "looks up an account",
            "parametersJson": '{"type":"object"}',
        }],

        responseSchemaJson='{"type":"object"}',
        temperature=0.2,
        maxTokens=256,
        seed=7,
        stop=["END"],
        providerOptionsJson='{"thinking":true}')


@pytest.fixture
def expected_prompt_request() -> PromptRequest:
    return PromptRequest(
        prompt="wire the money",
        session_id="trip-3",
        history=(AgentTurn(prompt="hello", answer="hi"),),

        tool_exchanges=(
            ToolExchange(
                call_id="call-1",
                tool_name="lookup",
                arguments_json='{"account":"42"}',
                result="owed: 12"),),

        response_schema_json='{"type":"object"}',
        temperature=0.2,
        max_tokens=256,
        seed=7,
        stop=("END",),

        caller_tools=(
            ToolDefinition(
                name="lookup",
                description="looks up an account",
                parameters_json='{"type":"object"}'),),

        provider_options_json='{"thinking":true}')


@pytest.fixture
def held_effect() -> AgentEffect:
    return dataclasses.replace(
        AgentEffect.create(
            run_id="run-9",
            tool_name="wire",
            arguments='{"amount":100}',
            risk_level=RiskLevel.IRREVERSIBLE,
            approval_required=True,
            principal=AgentPrincipal(id="hassan", tenant_id="peerllm"),
            scope="account:42"),
        call_id="call-7")
