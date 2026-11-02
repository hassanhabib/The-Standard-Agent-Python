# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# SPEC.md 4.2 across HTTP: 6.0.0 let a request ask for citation, and the V1 run request had no
# field to ask with, so a caller of a deployment that expressed no opinion could never get the
# sources. The real agent stands behind the door here, because the rule being pinned (what the
# deployment configured wins over what the request asks) lives in the agent, not the host.

from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.standard_agent import StandardAgent

_REFUNDS_SOURCE = "Refund Policy (2026)"
_REFUNDS_ANSWER = "Enterprise customers may request a refund within 90 days."


def _refunds_grounding() -> list[KnowledgeResult]:
    return [
        KnowledgeResult(
            text="Refund policy. Enterprise customers may request a refund within 90 days.",
            score=0.91,
            source=_REFUNDS_SOURCE)]


def _grounded_agent(configure):
    knowledge_results = _refunds_grounding()

    async def retrieve(query):
        return knowledge_results

    async def brain(system_prompt, user_prompt):
        return f"FINAL: {_REFUNDS_ANSWER}"

    grounded_agent = (
        StandardAgent()
        .without_memory()
        .on_sourced_knowledge(retrieve)
        .on_brain(brain))

    configured_agent = configure(grounded_agent)

    return lambda principals: configured_agent


async def _post_citation_run(serve_host, v1_document, configure, cite_knowledge):
    async with serve_host(agent_factory=_grounded_agent(configure)) as client:
        response = await client.post_json(
            "api/V1/agents/runs",
            v1_document(prompt="what is the refund window?", citeKnowledge=cite_knowledge))

    assert response.status == 200

    return response.json()


async def test_should_cite_the_sources_when_the_request_asks_through_http(serve_host, v1_document):
    # given: a deployment that expressed no opinion, and a caller who asks
    expected_result = f"{_REFUNDS_ANSWER}\n\nSource: {_REFUNDS_SOURCE}"

    # when
    actual_response = await _post_citation_run(
        serve_host, v1_document, lambda agent: agent, cite_knowledge=True)

    # then
    assert actual_response["result"] == expected_result
