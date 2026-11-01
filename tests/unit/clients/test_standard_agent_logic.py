# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.clients.agents.exceptions import InvalidAgentCompositionException
from standard_agents.standard_agent import StandardAgent


async def test_should_compose_and_process_prompt(create_fully_stubbed_agent):
    # given
    agent = create_fully_stubbed_agent("FINAL: 42")

    # when
    actual_result = await agent.process_prompt(prompt="what is the answer?")

    # then
    assert actual_result == "42"


async def test_should_configure_brain_from_constructor_arguments(
        create_skill_broker,
        empty_memory_broker,
        empty_knowledge_broker):

    # given
    agent = (StandardAgent(api_url="https://api.peerllm.invalid/v1/", api_key="key", model="model")
        .use_skills(create_skill_broker())
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker))

    # when
    try:
        await agent.process_prompt(prompt="what is the answer?")
        actual_exception = None
    except Exception as exception:
        actual_exception = exception

    # then
    assert type(actual_exception) is not InvalidAgentCompositionException


def test_should_return_same_instance_on_each_builder_method():
    # given
    agent = StandardAgent()

    # when
    chained = (agent
        .skills(path="Skills")
        .brain(api_url="https://x/", api_key="key", model="model")
        .memory(path="memory.txt")
        .knowledge(path="Knowledge")
        .mcp(endpoint_url="https://mcp/")
        .log_to(path="log.txt"))

    # then
    assert chained is agent
