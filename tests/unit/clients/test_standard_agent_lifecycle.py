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
