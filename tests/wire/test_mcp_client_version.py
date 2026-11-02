# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The version an MCP client introduces itself with.

C# sends its assembly version in initialize's clientInfo (McpBroker.cs, StdioMcpBroker.cs:
typeof(...).Assembly.GetName().Version). The Python twin is the installed distribution's version,
read by the distribution's name, which is the-standard-agent. No C# test pins the version (the
C# wire test checks only clientInfo's name), so these have no C# twin.
"""

import http
import importlib.metadata
import json

import pytest

from tests.wire.scripted_server_handler import ScriptedResponse, ScriptedServerHandler
from tests.wire.scripted_stdio_server import ScriptedStdioServer
from tests.wire.test_mcp_wire_contract import create_broker as create_http_broker
from tests.wire.test_stdio_mcp_wire_contract import answer, answer_initialize
from tests.wire.test_stdio_mcp_wire_contract import create_broker as create_stdio_broker

INSTALLED_VERSION = "6.0.0.0"


@pytest.fixture
def installed_as_the_standard_agent(monkeypatch):
    """The metadata an installed the-standard-agent answers with, and nothing else installed."""
    real_version = importlib.metadata.version

    def version(distribution_name: str) -> str:
        if distribution_name == "the-standard-agent":
            return INSTALLED_VERSION

        if distribution_name == "standard-agents":
            raise importlib.metadata.PackageNotFoundError(distribution_name)

        return real_version(distribution_name)

    monkeypatch.setattr(importlib.metadata, "version", version)


async def test_should_introduce_itself_with_the_installed_version_over_http(
        installed_as_the_standard_agent):

    # given
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
    broker = create_http_broker(server)

    # when
    await broker.list_tools()

    # then
    initialize = json.loads(server.bodies[0])
    assert initialize["params"]["clientInfo"]["version"] == INSTALLED_VERSION

