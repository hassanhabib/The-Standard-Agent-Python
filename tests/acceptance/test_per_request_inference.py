# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Per-request inference (docs/per-request-inference.md).

One composed agent is configured once and asked many times; a request carries its own inference
options, and precedence (configured, then request, then framework default) is resolved once, at
the boundary. These pin the request seam: what a caller may shape, what the deployment always
wins, and what degrades gracefully.
"""

from unittest.mock import create_autospec

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.standard_agent import StandardAgent


def _shell() -> StandardAgent:
    skill_broker = create_autospec(SkillBroker, instance=True)
    skill_broker.select_skills.return_value = [Skill(content="You are a helpful agent.")]

    memory_broker = create_autospec(MemoryBroker, instance=True)
    memory_broker.select_memories.return_value = []

    knowledge_broker = create_autospec(KnowledgeBroker, instance=True)
    knowledge_broker.select_knowledge.return_value = []

    return (StandardAgent()
        .use_skills(skill_broker)
        .use_memory(memory_broker)
        .use_knowledge(knowledge_broker))


def _agent_with(brain) -> StandardAgent:
    return _shell().on_brain(brain)


def _brain_answering(*replies: str):
    """A brain that answers each call with the next reply, and with the last one after that."""
    call = 0

    async def brain(system_prompt, user_prompt):
        nonlocal call
        reply = replies[min(call, len(replies) - 1)]
        call += 1

        return reply

    return brain


# The request's schema seeds the guardian, not only the wire (design 4.1): plenty of engines
# accept response_format and quietly ignore it, and this brain ignores everything, so the only
# thing standing between the caller and a misshapen answer is the guardian holding the draft to
# the requested shape and sending it back.
async def test_should_hold_the_answer_to_the_request_schema_when_no_contract_is_configured():
    # given: a brain whose first draft breaks the requested shape and whose second matches
    agent = _agent_with(_brain_answering("FINAL: Paris", 'FINAL: {"city":"Paris"}'))

    request = PromptRequest(
        prompt="capital of France, as JSON",
        response_schema_json='{"type":"object","required":["city"]}')

    # when
    actual_result = await agent.process_prompt(request)

    # then: the malformed draft was revised against the schema the request asked for
    assert actual_result == '{"city":"Paris"}'


# Configuration is a ceiling, not a suggestion (design 4). The first draft matches the REQUEST's
# shape exactly, and is still revised, because a configured Contract discards the request's
# schema outright. Never merged, never partially honored: the model is constrained to one schema
# and validated against that same schema, which is what makes the
# constrained-to-A-validated-against-B loop unreachable.
async def test_should_discard_the_request_schema_when_a_contract_is_configured():
    # given: a configured Contract requiring "city", a request asking for "name"
    agent = (_agent_with(_brain_answering('FINAL: {"name":"Paris"}', 'FINAL: {"city":"Paris"}'))
        .contract('{"type":"object","required":["city"]}'))

    request = PromptRequest(
        prompt="capital of France, as JSON",
        response_schema_json='{"type":"object","required":["name"]}')

    # when
    actual_result = await agent.process_prompt(request)

    # then: configured won; the draft shaped like the request was sent back
    assert actual_result == '{"city":"Paris"}'


class _CapturingGeneratorBroker(GeneratorBroker):
    """A broker that opts in: it takes the resolved options and says so.

    What it captures is the resolution's OUTPUT: a broker below the boundary writes what it is
    given and decides nothing (design 4.2).
    """

    def __init__(self) -> None:
        self.captured: ResolvedInference | None = None

    @property
    def honors_request(self) -> bool:
        return True

    async def generate(self, system_prompt, user_prompt, *, inference=None):
        if inference is not None:
            self.captured = inference

        return "FINAL: ok"

    async def generate_stream(self, system_prompt, user_prompt, *, inference=None):
        if inference is not None:
            self.captured = inference

        yield "FINAL: ok"


def _agent_with_broker(broker: GeneratorBroker) -> StandardAgent:
    return _shell().use_generator(broker)


# 4.2's exact blocker, pinned: the host called brain() and said nothing about temperature.
# "Configured wins" must mean HARD-configured wins: a request beaten by a default nobody
# expressed an opinion about would make per-request inference unimplementable.
async def test_should_let_the_request_speak_where_the_deployment_said_nothing():
    # given: a brain configured with no opinion on temperature or max tokens
    broker = _CapturingGeneratorBroker()

    agent = (_agent_with_broker(broker)
        .brain("http://localhost:9999/v1/", api_key="", model="test"))

    request = PromptRequest(prompt="hello", temperature=0.9, max_tokens=512)

    # when
    await agent.process_prompt(request)

    # then: the request's values reached the wire
    assert broker.captured is not None
    assert broker.captured.temperature == 0.9
    assert broker.captured.max_tokens == 512
