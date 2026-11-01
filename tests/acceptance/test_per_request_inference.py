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

from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
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
