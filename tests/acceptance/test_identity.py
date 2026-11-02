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


async def test_should_let_policy_refuse_an_act_on_the_identity_alone():
    # given: the same act, permitted for one principal and not the other
    tool = _CountingTool()
    second_prompt = ""
    brain_calls = 0

    async def generate(system_prompt, user_prompt):
        nonlocal brain_calls, second_prompt
        brain_calls += 1

        if brain_calls > 1:
            second_prompt = user_prompt

        return "ACTION: wire_transfer: 10000" if brain_calls == 1 else "FINAL: I could not do that"

    async def authorize(effect):
        return (
            AuthorizationDecision.allow() if effect.principal == "teller-42"
            else AuthorizationDecision.deny(f"'{effect.principal}' may not move money"))

    agent = (StandardAgent()
        .on_skills(_select_no_skills)
        .on_memory(_recall_nothing, _remember_nothing)
        .on_knowledge(_retrieve_nothing)
        .tool(tool)
        .principal(lambda: "intern-9")
        .on_brain(generate)
        .on_policy(authorize))

    # when
    actual_result = await agent.process_prompt("pay the invoice")

    # then: the denial names who was refused, which is what makes it reviewable
    assert tool.execution_count == 0
    assert "'intern-9' may not move money" in second_prompt
    assert actual_result == "I could not do that"


async def test_should_carry_the_whole_identity_into_the_authorization_decision():
    """An identifier alone answers "who" and nothing else. A policy engine is routinely written
    as "this principal, in this tenant, under this jurisdiction", and a delegated act, where a
    service acts on a person's behalf, is a different question from that service acting for
    itself (SPEC.md 4.9)."""
    # given
    tool = _CountingTool()
    seen_by_policy = None

    async def authorize(effect):
        nonlocal seen_by_policy
        seen_by_policy = effect.identity

        return AuthorizationDecision.allow()

    agent = (_agent_that_calls_the_tool(tool, "ACTION: wire_transfer: 10000", "FINAL: paid")
        .principal(lambda: AgentPrincipal(
            id="svc-payments",
            tenant_id="acme-eu",
            jurisdiction="EU",
            delegated_by="teller-42"))
        .on_policy(authorize))

    # when
    await agent.process_prompt("pay the invoice")

    # then
    assert seen_by_policy is not None
    assert seen_by_policy.id == "svc-payments"
    assert seen_by_policy.tenant_id == "acme-eu"
    assert seen_by_policy.jurisdiction == "EU"
    assert seen_by_policy.delegated_by == "teller-42"


async def test_should_refuse_an_act_on_jurisdiction_alone():
    # given: the same act, by the same principal, permitted in one regime and not another
    tool = _CountingTool()

    async def authorize(effect):
        jurisdiction = None if effect.identity is None else effect.identity.jurisdiction

        return (
            AuthorizationDecision.allow() if jurisdiction == "US"
            else AuthorizationDecision.deny("cross-border transfers need US booking"))

    agent = (_agent_that_calls_the_tool(
            tool, "ACTION: wire_transfer: 10000", "FINAL: I could not do that")
        .principal(lambda: AgentPrincipal(id="teller-42", jurisdiction="EU"))
        .on_policy(authorize))

    # when
    await agent.process_prompt("pay the invoice")

    # then
    assert tool.execution_count == 0


async def test_should_keep_the_identifier_only_principal_working():
    """The id-only overload still works and still reads the same way, so nothing written
    against 1.0 has to change to keep authorizing."""
    # given
    tool = _CountingTool()
    seen_id = None
    seen_identity = None

    async def authorize(effect):
        nonlocal seen_id, seen_identity
        seen_id = effect.principal
        seen_identity = effect.identity

        return AuthorizationDecision.allow()

    agent = (_agent_that_calls_the_tool(tool, "ACTION: wire_transfer: 10000", "FINAL: paid")
        .principal(lambda: "teller-42")
        .on_policy(authorize))

    # when
    await agent.process_prompt("pay the invoice")

    # then: the id reads as before, and the richer view carries the same identity
    assert seen_id == "teller-42"
    assert seen_identity.id == "teller-42"
    assert seen_identity.tenant_id is None


async def test_should_carry_no_principal_when_none_is_configured():
    # given: the neutral case: nothing configured, nothing asserted about identity
    tool = _CountingTool()
    policy_ran = False
    seen_by_policy = "not asked"

    async def authorize(effect):
        nonlocal policy_ran, seen_by_policy
        policy_ran = True
        seen_by_policy = effect.principal

        return AuthorizationDecision.allow()

    agent = (_agent_that_calls_the_tool(tool, "ACTION: wire_transfer: 10000", "FINAL: paid")
        .on_policy(authorize))

    # when
    await agent.process_prompt("pay the invoice")

    # then: absent an identity the effect claims none, rather than inventing one
    assert policy_ran
    assert seen_by_policy is None
