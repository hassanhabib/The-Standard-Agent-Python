# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""A budget that only applies to one protocol is not a budget.

Token spend was read from what the provider REPORTED, and only the native V1 path has a report
to read. On the text protocol prompt_tokens and completion_tokens stayed zero, the run added
zero to its spend every turn, and budget(max_tokens=...) / budget(max_cost_usd=...) never
tripped, while the Enterprise profile went on claiming budgets. V0 is not deprecated; it is the
contract that works against any endpoint, which makes it the likelier half of the estate to be
running.

Measuring is Decision's (a token is the model's unit). Deciding whether to continue is the
loop's. These tests pin the seam from the outside, through the builder, because that is the
only place a caller can tell whether the control they configured actually exists.
"""

from decimal import Decimal

from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


class _CountingTool(Tool):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates arithmetic."

    async def execute(self, input: str) -> str:
        self.calls += 1

        return "2"


async def _select_no_skills():
    return []


async def _recall_nothing():
    return []


async def _remember_nothing(memory):
    return None


async def _retrieve_nothing(query):
    return []


def _agent_with(brain, tool: Tool) -> StandardAgent:
    return (StandardAgent()
        .on_skills(_select_no_skills)
        .on_memory(_recall_nothing, _remember_nothing)
        .on_knowledge(_retrieve_nothing)
        .tool(tool)
        .on_brain(brain))


async def _always_calls_the_tool(system_prompt, user_prompt):
    """A brain that never finishes: every turn asks for the tool again, so only a budget or the
    turn cap can end the run. With the budget far below what the exchange costs, the budget has
    to be what ends it."""
    return "ACTION: calculator: 1+1"


async def test_should_exhaust_the_token_budget_on_the_text_protocol():
    # given
    tool = _CountingTool()

    agent = _agent_with(_always_calls_the_tool, tool).max_turns(20).budget(max_tokens=40)

    # when
    actual_result = await agent.process_prompt("what is one plus one")

    # then: a text-protocol run consumes tokens like any other, so the budget it was given has
    # to be the thing that stops it, rather than the turn cap
    assert "token budget" in actual_result
    assert tool.calls < 20


async def test_should_exhaust_the_cost_budget_on_the_text_protocol():
    # given
    tool = _CountingTool()

    agent = (_agent_with(_always_calls_the_tool, tool)
        .max_turns(20)
        .budget(max_cost_usd=Decimal("0.0001"), cost_per_thousand_tokens=Decimal(1)))

    # when
    actual_result = await agent.process_prompt("what is one plus one")

    # then: cost is priced off the token count, so a protocol that reports no tokens reports
    # no cost, and the bound silently never applies
    assert "cost budget" in actual_result
