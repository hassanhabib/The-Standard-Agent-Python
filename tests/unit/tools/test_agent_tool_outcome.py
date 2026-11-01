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
