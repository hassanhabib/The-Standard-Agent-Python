# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import ANY, call, create_autospec

import pytest

from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent
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


async def test_should_apply_handoff_template_on_execute(nested_agent, create_random_string):
    # given
    random_input = create_random_string()
    random_answer = create_random_string()
    handoff = "You are a researcher. Research this and report: {input}"
    expected_handoff_prompt = f"You are a researcher. Research this and report: {random_input}"

    nested_agent.run.return_value = AgentOutcome(random_answer, AgentStatus.RESPONDED)

    agent_tool = AgentTool(name="researcher", agent=nested_agent, handoff=handoff)

    # when
    actual_output = await agent_tool.execute(random_input)

    # then
    assert actual_output == random_answer
    assert nested_agent.mock_calls == [call.run(expected_handoff_prompt, cancellation=ANY)]


def test_should_expose_description_and_parameters_on_agent_tool(nested_agent):
    # given
    description = "Delegates a research question to a specialist."
    parameters = '{"query":"string"}'

    agent_tool = AgentTool(
        name="researcher",
        agent=nested_agent,
        description=description,
        parameters=parameters)

    # then
    assert agent_tool.description == description
    assert agent_tool.parameters == parameters


async def test_should_nest_agent_inside_agent(
        nested_agent,
        create_skill_broker,
        empty_memory_broker,
        empty_knowledge_broker):

    # given: the inner agent answers anything with a fixed finding
    nested_agent.run.return_value = AgentOutcome("the capital is Paris", AgentStatus.RESPONDED)
    researcher = AgentTool(name="researcher", agent=nested_agent)

    outer_brain = create_autospec(GeneratorBroker, instance=True)
    outer_brain.honors_request = False
    outer_brain.generate.side_effect = ["ACTION: researcher: capital of France", "FINAL: Paris"]

    gate = create_autospec(ClassifierBroker, instance=True)
    gate.classify.return_value = "allow"
    gate.assess.return_value = None
    judge = create_autospec(VerifierBroker, instance=True)
    judge.verify.return_value = "1.0"
    mcp = create_autospec(McpBroker, instance=True)
    mcp.list_tools.return_value = []

    outer_agent = (StandardAgent()
        .use_skills(create_skill_broker(Skill(content="you are an agent")))
        .use_generator(outer_brain)
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .use_gate(gate)
        .use_judge(judge)
        .use_mcp(mcp)
        .use_logging(create_autospec(LoggingBroker, instance=True))
        .tool(researcher))

    # when
    actual_result = await outer_agent.process_prompt(prompt="what is the capital of France?")

    # then
    assert actual_result == "Paris"
    nested_agent.run.assert_awaited_once_with("capital of France", cancellation=ANY)
