# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import pytest

from standard_agents.models.clients.agents.exceptions import InvalidAgentCompositionException
from standard_agents.models.loggings.trace_verbosity import TraceVerbosity
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


def test_should_chain_log_to_with_verbosity():
    # given
    agent = StandardAgent()

    # when
    chained = agent.log_to(path="log.txt", verbosity=TraceVerbosity.NATURES)

    # then
    assert chained is agent


async def test_should_recompose_after_configuration_changes(
        create_fully_stubbed_agent,
        create_generator_broker):

    # given
    agent = create_fully_stubbed_agent("FINAL: first")
    first_result = await agent.process_prompt(prompt="prompt")
    new_generator = create_generator_broker("FINAL: second")

    # when
    agent.use_generator(new_generator)
    second_result = await agent.process_prompt(prompt="prompt")

    # then
    assert first_result == "first"
    assert second_result == "second"


async def test_should_throw_composition_exception_on_process_prompt_if_brain_is_not_configured():
    # given
    agent = StandardAgent()

    # when
    process_task = agent.process_prompt(prompt="prompt")

    with pytest.raises(InvalidAgentCompositionException) as raised:
        await process_task

    # then
    assert "no brain" in raised.value.message
