# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Identity-aware authorization (SPEC.md 4.9).

The Enterprise profile claims it, and the claim is only true if the principal reaches the
decision, not merely the record of it. A policy engine asked "may this act happen?" without
being told whose act it is can answer nothing about identity, however faithfully the audit log
names the caller afterwards.
"""

from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision)
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


class _CountingTool(Tool):
    def __init__(self) -> None:
        self.execution_count = 0

    @property
    def name(self) -> str:
        return "wire_transfer"

    @property
    def description(self) -> str:
        return "Moves money."

    async def execute(self, input: str) -> str:
        self.execution_count += 1

        return "transfer complete"


async def _select_no_skills():
    return []


async def _recall_nothing():
    return []


async def _remember_nothing(memory):
    return None


async def _retrieve_nothing(query):
    return []


def _agent_that_calls_the_tool(tool: _CountingTool, *replies: str) -> StandardAgent:
    scripted_replies = list(replies)

    async def generate(system_prompt, user_prompt):
        return scripted_replies.pop(0) if scripted_replies else "FINAL: done"

    return (StandardAgent()
        .on_skills(_select_no_skills)
        .on_memory(_recall_nothing, _remember_nothing)
        .on_knowledge(_retrieve_nothing)
        .tool(tool)
        .on_brain(generate))


async def test_should_carry_the_principal_into_the_authorization_decision():
    # given
    tool = _CountingTool()
    seen_by_policy = None

    async def authorize(effect):
        nonlocal seen_by_policy
        seen_by_policy = effect.principal

        return AuthorizationDecision.allow()

    agent = (_agent_that_calls_the_tool(tool, "ACTION: wire_transfer: 10000", "FINAL: paid")
        .principal(lambda: "teller-42")
        .on_policy(authorize))

    # when
    await agent.process_prompt("pay the invoice")

    # then: an audit trail that names the caller after the fact is not authorization
    assert seen_by_policy == "teller-42"
