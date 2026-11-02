# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# No C# twin: a Python addition (owner's decision, 2026-11-02). C#'s StandardAgent never disposes
# the MCP servers it starts and relies on the host exiting; an agent here may also be closed,
# with aclose() or async with, and stops what it owns: the MCP server processes it started.
# What the host handed it (a broker, an HTTP handler) is the host's, and is left as it is.

import io
import itertools
import re
import sys
import urllib.request
import urllib.response
from email.message import Message
from pathlib import Path

import pytest

from standard_agents.brokers.mcps.stdio_mcp_broker import StdioMcpBroker
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.standard_agent import StandardAgent
from tests.wire.processes import have_stopped, is_running

PROCESS_SERVER_PATH = str(Path(__file__).parents[2] / "wire" / "stdio_process_server.py")

EMPTY_TOOL_LIST = '{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}'


class HostHandler(urllib.request.HTTPHandler):
    """The host's handler: answers every request with an empty tool list, and records whether
    it was used and whether anyone closed it."""

    def __init__(self) -> None:
        super().__init__()
        self.request_count = 0
        self.is_closed = False

    def http_open(self, request: urllib.request.Request):
        self.request_count += 1
        headers = Message()
        headers["Content-Type"] = "application/json; charset=utf-8"

        response = urllib.response.addinfourl(
            io.BytesIO(EMPTY_TOOL_LIST.encode("utf-8")),
            headers,
            request.full_url,
            200)

        response.msg = "OK"

        return response

    def close(self) -> None:
        self.is_closed = True


async def select_persona():
    return [Skill(name="persona", content="Your tools:\n{{tools}}")]


def create_agent(memory_broker, knowledge_broker, system_prompts: list[str]) -> StandardAgent:
    """An agent that starts the process server, and records every system prompt it is given."""

    async def brain(system_prompt, user_prompt):
        system_prompts.append(system_prompt)

        return "FINAL: done"

    return (StandardAgent()
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .on_skills(select_persona)
        .mcp_process(sys.executable, arguments=[PROCESS_SERVER_PATH])
        .on_brain(brain))


def create_calling_agent(
        memory_broker,
        knowledge_broker,
        tool_answers: list[str]) -> StandardAgent:
    """An agent that starts the process server and, on every prompt, calls one of its tools
    once, recording the prompt that carries the server's answer."""
    turns = itertools.count(1)

    async def brain(system_prompt, user_prompt):
        if next(turns) % 2 == 1:
            tool_name = re.search(r"\bserver-\d+\b", system_prompt).group()

            return f"ACTION: {tool_name}: now"

        tool_answers.append(user_prompt)

        return "FINAL: done"

    return (StandardAgent()
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker)
        .on_skills(select_persona)
        .mcp_process(sys.executable, arguments=[PROCESS_SERVER_PATH])
        .on_brain(brain))


def process_ids_answered(tool_answers: list[str]) -> list[int]:
    """The server's process id and its child's, as the server running at the last call had
    them."""
    server_id, child_id = re.findall(r"\bserver-(\d+) child-(\d+)\b", tool_answers[-1])[-1]

    return [int(server_id), int(child_id)]


async def process_ids_of(agent: StandardAgent, system_prompts: list[str]) -> list[int]:
    """Runs the agent, and returns the server's process id and its child's, as it advertised
    them."""
    await agent.process_prompt("hello")

    process_ids = [
        int(process_id)
        for process_id in re.findall(r"\b(?:server|child)-(\d+)\b", system_prompts[-1])]

    assert process_ids, "the agent advertised no server process"

    return process_ids


async def test_should_stop_every_mcp_server_process_it_started_when_closed(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: an agent that started an MCP server, which started a child of its own
    system_prompts = []
    agent = create_agent(empty_memory_broker, empty_knowledge_broker, system_prompts)
    process_ids = await process_ids_of(agent, system_prompts)

    # when
    await agent.aclose()

    # then: the whole tree is gone
    assert await have_stopped(process_ids)


async def test_should_stop_every_mcp_server_process_it_started_when_its_block_ends(
        empty_memory_broker,
        empty_knowledge_broker):

    # given, when: an agent that started an MCP server, used inside an async with block
    system_prompts = []

    async with create_agent(
            empty_memory_broker,
            empty_knowledge_broker,
            system_prompts) as agent:

        process_ids = await process_ids_of(agent, system_prompts)

    # then: the whole tree is gone
    assert await have_stopped(process_ids)


async def test_should_stop_every_mcp_server_process_it_started_when_its_block_raises(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: an agent that started an MCP server, used inside an async with block that raises
    system_prompts = []
    process_ids = []

    # when
    with pytest.raises(LookupError):
        async with create_agent(
                empty_memory_broker,
                empty_knowledge_broker,
                system_prompts) as agent:

            process_ids.extend(await process_ids_of(agent, system_prompts))

            raise LookupError("the host failed with the agent in hand")

    # then: the whole tree is gone, and the host's error is the one that surfaced
    assert await have_stopped(process_ids)


async def test_should_close_an_agent_already_closed(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: an agent that started an MCP server, and was closed
    system_prompts = []
    agent = create_agent(empty_memory_broker, empty_knowledge_broker, system_prompts)
    process_ids = await process_ids_of(agent, system_prompts)
    await agent.aclose()

    # when
    await agent.aclose()

    # then: closing again is harmless
    assert await have_stopped(process_ids)


async def test_should_close_an_agent_that_never_ran(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: an agent configured with an MCP server, never run, so nothing is composed or started
    system_prompts = []
    agent = create_agent(empty_memory_broker, empty_knowledge_broker, system_prompts)

    # when
    await agent.aclose()

    # then: closing it is harmless, and nothing ran
    assert system_prompts == []


async def test_should_stop_the_mcp_server_processes_of_an_earlier_composition_when_closed(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: an agent that started an MCP server, was configured again after it ran, and so
    # composed afresh and started a second one, leaving the first running
    system_prompts = []
    agent = create_agent(empty_memory_broker, empty_knowledge_broker, system_prompts)
    earlier_process_ids = await process_ids_of(agent, system_prompts)
    agent.max_turns(5)
    later_process_ids = await process_ids_of(agent, system_prompts)

    # when
    await agent.aclose()

    # then: every server the agent started is gone, not only the latest composition's
    assert await have_stopped(earlier_process_ids + later_process_ids)


async def test_should_not_stop_an_mcp_server_the_host_supplied_when_closed(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: an MCP server the host started and handed to the agent, which ran with it
    async def brain(system_prompt, user_prompt):
        return "FINAL: done"

    async with StdioMcpBroker(
            command=sys.executable,
            arguments=[PROCESS_SERVER_PATH],
            timeout_seconds=30) as host_broker:

        process_ids = [int(tool.name.split("-")[1]) for tool in await host_broker.list_tools()]

        agent = (StandardAgent()
            .use_memory(empty_memory_broker)
            .use_knowledge(empty_knowledge_broker)
            .use_mcp(host_broker)
            .on_brain(brain))

        await agent.process_prompt("hello")

        # when
        await agent.aclose()

        # then: the host's server is the host's to stop, and is still running
        assert all(is_running(process_id) for process_id in process_ids)


async def test_should_not_close_an_http_handler_the_host_supplied_when_closed(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: an agent whose MCP server over HTTP rides the host's handler, and which ran with it
    host_handler = HostHandler()

    async def brain(system_prompt, user_prompt):
        return "FINAL: done"

    agent = (StandardAgent()
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .mcp("http://mcp.test/")
        .http(lambda: host_handler)
        .on_brain(brain))

    await agent.process_prompt("hello")

    # when
    await agent.aclose()

    # then: the agent used the host's handler, and left it to the host
    assert host_handler.request_count > 0
    assert host_handler.is_closed is False


async def test_should_answer_when_used_again_after_closing(
        empty_memory_broker,
        empty_knowledge_broker):

    # given: an agent that ran, calling its MCP server, and was closed
    tool_answers = []
    agent = create_calling_agent(empty_memory_broker, empty_knowledge_broker, tool_answers)
    await agent.process_prompt("hello")
    closed_process_ids = process_ids_answered(tool_answers)
    await agent.aclose()

    try:
        # when
        answer = await agent.process_prompt("hello again")

        # then: it answered through a server started again, which is running
        restarted_process_ids = process_ids_answered(tool_answers)

        assert answer == "done"
        assert restarted_process_ids != closed_process_ids
        assert all(is_running(process_id) for process_id in restarted_process_ids)
    finally:
        await agent.aclose()

