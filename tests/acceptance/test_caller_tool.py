# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Caller tools (docs/per-request-inference.md 6).

In the OpenAI protocol the server never executes a caller's tool: the model names one, the
server returns the call, and the CALLER executes it and posts the result back. Caller tools are
therefore vocabulary handed to the model, never capability granted to the agent, and a call
naming one is a terminal answer addressed to the caller, riding the same pending-effect seam a
held approval rides.
"""

from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.sessions.file_session_broker import FileSessionBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.brokers.generators.v1.conversation import ToolDefinition
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent


@pytest.fixture
def sessions_path(tmp_path):
    return str(tmp_path / "standard-agent-caller-tools")


def _bare_agent() -> StandardAgent:
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = [Skill(content="You are a helpful agent.")]

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker))


def _agent_with(brain) -> StandardAgent:
    return _bare_agent().on_brain(brain)


def _send_email_tool() -> ToolDefinition:
    return ToolDefinition(
        name="send_email",
        description="Sends an email from the caller's own outbox.",
        parameters_json="{}")


# The foreign call is a pending effect: the run pauses, something outside this process must act
# and report back. Built for human approval, structurally identical here. The authority over
# this one is the caller.
async def test_should_treat_a_call_naming_a_caller_tool_as_a_terminal_answer(sessions_path):
    # given: a brain that wants the caller's tool, which the agent cannot and must not run
    async def brain(system_prompt, user_prompt):
        return 'ACTION: send_email: {"to":"jane@acme.com"}'

    agent = (_agent_with(brain)
        .sessions(sessions_path)
        .max_turns(2))

    request = PromptRequest(
        prompt="email jane the report",
        session_id="caller-run-1",
        caller_tools=(_send_email_tool(),))

    # when
    outcome = await agent.run(request)

    # then: the run paused rather than recovered, refused, or executed anything
    assert outcome.status is AgentStatus.AWAITING_INPUT
    assert "send_email" in outcome.result

    # and the call itself rode out on the session, so a different process can hand the caller
    # the act rather than only the news that something is waiting
    session = await FileSessionBroker(sessions_path).select_session("caller-run-1")

    assert session is not None
    assert session.pending_effect is not None
    assert session.pending_effect.tool_name == "send_email"
    assert "jane@acme.com" in session.pending_effect.arguments
