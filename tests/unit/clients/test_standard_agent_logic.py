# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio

import pytest

from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.clients.agents.exceptions import InvalidAgentCompositionException
from standard_agents.models.foundations.skills.skill import Skill
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


async def test_should_compose_on_process_prompt_if_generator_is_swapped_without_brain_settings(
        create_skill_broker,
        create_generator_broker,
        allowing_classifier_broker,
        passing_verifier_broker,
        empty_memory_broker,
        empty_knowledge_broker,
        create_mcp_broker,
        logging_broker):

    # given
    agent = (StandardAgent()
        .use_skills(create_skill_broker(Skill(content="skills")))
        .use_generator(create_generator_broker("FINAL: ok"))
        .use_gate(allowing_classifier_broker)
        .use_judge(passing_verifier_broker)
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .use_mcp(create_mcp_broker())
        .use_logging(logging_broker))

    # when
    actual_result = await agent.process_prompt(prompt="prompt")

    # then
    assert actual_result == "ok"


async def test_should_compose_bare_brain_on_process_prompt_without_guardians(
        create_skill_broker,
        empty_memory_broker,
        create_generator_broker):

    # given
    agent = (StandardAgent()
        .use_skills(create_skill_broker())
        .use_memory(empty_memory_broker)
        .use_generator(create_generator_broker("Hello there!")))

    # when
    actual_result = await agent.process_prompt(prompt="Hi there!")

    # then
    assert actual_result == "Hello there!"


async def test_should_compose_core_profile_agent_on_process_prompt_without_mcp_configured(
        create_skill_broker,
        create_generator_broker,
        allowing_classifier_broker,
        passing_verifier_broker,
        empty_memory_broker,
        empty_knowledge_broker):

    # given
    agent = (StandardAgent()
        .use_skills(create_skill_broker(Skill(content="skills")))
        .use_generator(create_generator_broker("FINAL: composed"))
        .use_gate(allowing_classifier_broker)
        .use_judge(passing_verifier_broker)
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker))

    # when
    actual_result = await agent.process_prompt(prompt="prompt")

    # then
    assert actual_result == "composed"


async def test_should_recover_from_unknown_tool_without_mcp_configured(
        create_skill_broker,
        create_generator_broker,
        allowing_classifier_broker,
        passing_verifier_broker,
        empty_memory_broker,
        empty_knowledge_broker):

    # given: the Brain calls a tool that does not exist, then answers
    agent = (StandardAgent()
        .use_skills(create_skill_broker(Skill(content="skills")))
        .use_generator(create_generator_broker(
            "ACTION: weather: today",
            "FINAL: could not get weather"))
        .use_gate(allowing_classifier_broker)
        .use_judge(passing_verifier_broker)
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker))

    # when
    actual_result = await agent.process_prompt(prompt="weather today?")

    # then
    assert actual_result == "could not get weather"


async def test_should_stream_response_on_stream_prompt(
        create_skill_broker,
        empty_memory_broker,
        create_generator_broker):

    # given
    async def to_async_stream(*tokens):
        for token in tokens:
            await asyncio.sleep(0)

            yield token

    generator_broker = create_generator_broker("")

    generator_broker.generate_stream.side_effect = (
        lambda system_prompt, user_prompt, inference=None: to_async_stream("Hi ", "there."))

    agent = (StandardAgent()
        .use_skills(create_skill_broker())
        .use_memory(empty_memory_broker)
        .use_generator(generator_broker))

    # when
    actual_events = [
        stream_event async for stream_event in agent.process_prompt_stream(prompt="Hi there!")]

    # then
    streamed_response = "".join(
        stream_event.content for stream_event in actual_events
        if stream_event.type is AgentStreamEventType.RESPONSE)

    assert streamed_response == "Hi there."


async def test_should_use_custom_brain_on_process_prompt(create_skill_broker, empty_memory_broker):
    # given
    expected_answer = "answer from the custom brain"

    async def brain(system_prompt, user_prompt):
        return expected_answer

    agent = (StandardAgent()
        .use_skills(create_skill_broker())
        .use_memory(empty_memory_broker)
        .on_brain(brain))

    # when
    actual_result = await agent.process_prompt(prompt="compute something")

    # then
    assert actual_result == expected_answer


async def test_should_advertise_only_described_tools_at_tools_marker_on_process_prompt(
        create_skill_broker,
        empty_memory_broker,
        create_generator_broker,
        create_tool):

    # given
    generator_broker = create_generator_broker("FINAL: done")
    described_tool = create_tool("calculator", "Evaluate arithmetic.", "{}")
    hidden_tool = create_tool("secret", "")

    agent = (StandardAgent()
        .use_skills(create_skill_broker(Skill(content="Tools:\n{{tools}}")))
        .use_memory(empty_memory_broker)
        .use_generator(generator_broker)
        .tool(described_tool)
        .tool(hidden_tool))

    # when
    await agent.process_prompt(prompt="compute something")

    # then
    captured_system_prompt = generator_broker.generate.call_args.args[0]

    assert "calculator" in captured_system_prompt
    assert "secret" not in captured_system_prompt
    assert "{{tools}}" not in captured_system_prompt


async def test_should_use_custom_gate_to_refuse_on_process_prompt(
        create_skill_broker,
        empty_memory_broker,
        empty_knowledge_broker):

    # given
    async def brain(system_prompt, user_prompt):
        return "FINAL: hello"

    async def gate(gate_rubric, prompt):
        return "refuse: not allowed"

    agent = (StandardAgent()
        .use_skills(create_skill_broker())
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_brain(brain)
        .on_gate(gate))

    # when
    actual_result = await agent.process_prompt(prompt="do something bad")

    # then
    assert actual_result == "I'm not able to help with that."
