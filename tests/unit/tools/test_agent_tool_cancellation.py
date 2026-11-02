# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Cancellation across the nesting seam. The how-to promises a cancelled run stops at the next
# turn boundary; a sub-agent runs its own loop with its own turn boundaries, so the outer signal
# must reach it, otherwise cancelling the outer run leaves the inner one running to its own cap,
# doing work nobody wants anymore.

import asyncio
import itertools

from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.agent_tool import AgentTool
from standard_agents.tools.tool import Tool


class CancellingTool(Tool):
    def __init__(self, outer_run: asyncio.Event) -> None:
        self.outer_run = outer_run
        self.execution_count = 0

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates arithmetic."

    @property
    def parameters(self) -> str:
        return "{}"

    async def execute(self, input: str) -> str:
        self.execution_count += 1
        self.outer_run.set()

        return "4183"


async def test_should_stop_the_nested_run_when_the_outer_run_is_cancelled(
        create_skill_broker,
        empty_memory_broker,
        empty_knowledge_broker):

    # given: an inner agent whose brain never terminates and proposes a DISTINCT act each turn
    # (an identical act would be spared by run-once and mask the leak), whose tool cancels the
    # OUTER run on its first execution, and enough inner turns that an unstopped inner run is
    # unmistakable in the count.
    outer_run = asyncio.Event()
    tool = CancellingTool(outer_run)
    inner_thoughts = itertools.count(1)

    async def inner_brain(system_prompt, user_prompt):
        return f"ACTION: calculator: {next(inner_thoughts)}"

    inner = (StandardAgent()
        .use_skills(create_skill_broker())
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_brain(inner_brain)
        .tool(tool)
        .max_turns(50))

    async def outer_brain(system_prompt, user_prompt):
        return "ACTION: sub: do the work"

    outer = (StandardAgent()
        .use_skills(create_skill_broker())
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_brain(outer_brain)
        .tool(AgentTool(name="sub", agent=inner))
        .max_turns(2))

    # when: the outer run is cancelled while the inner one is on its first turn
    await outer.process_prompt("delegate this", session_id="", cancellation=outer_run)

    # then: the inner loop observed the outer signal at its next turn boundary. Without the
    # signal crossing the seam it runs every turn of its cap for a run nobody wants.
    assert tool.execution_count == 1, (
        "cancelling the outer run must stop the nested run at its next turn boundary, not "
        + "leave it working to its own cap")
