# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# No C# twin: a Python addition (owner's decision, 2026-11-02). C#'s StandardAgent never disposes
# the MCP servers it starts and relies on the host exiting; an agent here may also be closed,
# with aclose() or async with, and stops what it owns: the MCP server processes it started.
# What the host handed it (a broker, an HTTP handler) is the host's, and is left as it is.

import re
import sys
from pathlib import Path

import pytest

from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.standard_agent import StandardAgent
from tests.wire.processes import have_stopped

PROCESS_SERVER_PATH = str(Path(__file__).parents[2] / "wire" / "stdio_process_server.py")


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
