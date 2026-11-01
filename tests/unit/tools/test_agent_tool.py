# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import ANY, call

import pytest

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.tools.agent_tool import AgentTool


async def test_should_run_nested_agent_as_tool(nested_agent, create_random_string):
    # given
    random_name = create_random_string()
    random_input = create_random_string()
    random_answer = create_random_string()
    expected_output = random_answer

    nested_agent.run.return_value = AgentOutcome(random_answer, AgentStatus.RESPONDED)

    agent_tool = AgentTool(name=random_name, agent=nested_agent)

    # when
    actual_output = await agent_tool.execute(random_input)

    # then
    assert actual_output == expected_output
    assert agent_tool.name == random_name
    assert nested_agent.mock_calls == [call.run(random_input, cancellation=ANY)]


async def test_should_propagate_on_execute_if_nested_agent_throws(nested_agent):
    # given
    nested_failure = RuntimeError("inner agent failed")
    nested_agent.run.side_effect = nested_failure

    agent_tool = AgentTool(name="nested", agent=nested_agent)

    # when
    with pytest.raises(RuntimeError) as raised:
        await agent_tool.execute(input="anything")

    # then
    assert str(raised.value) == "inner agent failed"
