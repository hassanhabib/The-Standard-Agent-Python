# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# A nested agent runs its own full loop, so it can end every way a run can end: answered,
# refused, held on an authority, out of turns. The outer agent sees one tool call and a string
# back, so it cannot tell WHICH of those happened.
#
# That is fine for an answer and dangerous for everything else. A sub-agent held on an approval
# returns "'wire_transfer' is waiting for approval before it can run.", prose that reads exactly
# like a result. The outer agent takes it as the tool's output, carries on, and may report the
# work as done when a human has not yet permitted it.

import pytest

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.tools.agent_tool import AgentTool


@pytest.fixture
def setup_nested_agent_ending(nested_agent):
    def setup(status, result):
        nested_agent.process_prompt.return_value = result
        nested_agent.run.return_value = AgentOutcome(result=result, status=status)

        return nested_agent

    return setup


async def test_should_return_the_answer_plainly_when_the_nested_agent_responded(
        setup_nested_agent_ending):

    # given
    nested = setup_nested_agent_ending(AgentStatus.RESPONDED, "the answer")
    agent_tool = AgentTool(name="researcher", agent=nested)

    # when
    actual_output = await agent_tool.execute("go")

    # then: an answer is an answer; nothing is added to it
    assert actual_output == "the answer"


@pytest.mark.parametrize(("status", "status_name"), [
    (AgentStatus.AWAITING_APPROVAL, "AwaitingApproval"),
    (AgentStatus.AWAITING_INPUT, "AwaitingInput"),
    (AgentStatus.REFUSED, "Refused"),
    (AgentStatus.FAILED, "Failed"),
])
async def test_should_mark_an_outcome_that_is_not_an_answer(
        setup_nested_agent_ending,
        status,
        status_name):

    # given
    nested = setup_nested_agent_ending(
        status,
        "'wire_transfer' is waiting for approval before it can run.")

    agent_tool = AgentTool(name="settlement", agent=nested)

    # when
    actual_output = await agent_tool.execute("pay it")

    # then: the outer agent must not be able to read this as a completed result. A run that was
    # held, refused or failed is not a tool result, and prose that merely mentions waiting is
    # indistinguishable from an answer that mentions it.
    assert actual_output.startswith("[did not complete]")

    # The outer agent has to know WHICH way it ended: held is not refused, and refused is not
    # failed.
    assert status_name in actual_output

    # The inner agent's own words are what say why; dropping them would leave the outer agent
    # with a category and no reason.
    assert "waiting for approval" in actual_output
