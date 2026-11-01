# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""SPEC.md 4.2: retrieval answers "what is relevant to this task", not "what exists".

The regression this pins is the one that made the feature look configured and return nothing:
matching the whole prompt literally against whole documents. A natural question never appears
verbatim inside its own answer, so the old implementation retrieved nothing for exactly the
queries a user asks.
"""

from unittest.mock import create_autospec

from standard_agents.brokers.files.local_file_broker import LocalFileBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.services.foundations.knowledges.knowledge_service import KnowledgeService
from standard_agents.standard_agent import StandardAgent


def _knowledge_over(knowledge_path, *documents: tuple[str, str]) -> KnowledgeService:
    knowledge_path.mkdir(parents=True, exist_ok=True)

    for name, body in documents:
        (knowledge_path / name).write_text(body, encoding="utf-8")

    return KnowledgeService(
        file_broker=LocalFileBroker(),
        knowledge_path=str(knowledge_path),
        search_pattern="*.md",
        max_results=1,
        logging_broker=create_autospec(LoggingBroker, instance=True))


# A parameter taken and never used: knowledge(min_score=) stored the floor in the door and the
# composition never passed it on, so a host raising the relevance floor changed nothing and was
# never told. The foundation honoured a floor all along; only the seam dropped it.
async def test_should_hold_knowledge_to_the_configured_relevance_floor(tmp_path):
    # given: one weakly-relevant document, and a floor set far above any real score
    knowledge_path = tmp_path / "knowledge"
    knowledge_path.mkdir()

    (knowledge_path / "pricing.md").write_text(
        "The pro plan pricing is $29 per month, billed annually.",
        encoding="utf-8")

    seen_by_brain = ""

    async def brain(system_prompt, user_prompt):
        nonlocal seen_by_brain
        seen_by_brain = user_prompt

        return "FINAL: ok"

    async def select_skills():
        return []

    async def recall():
        return []

    async def remember(memory):
        pass

    agent = (StandardAgent()
        .on_brain(brain)
        .on_skills(select_skills)
        .on_memory(recall=recall, remember=remember)
        .knowledge(str(knowledge_path), min_score=1_000.0))

    # when
    await agent.process_prompt("pro plan pricing")

    # then: nothing clears a floor of a thousand; injecting anyway means the floor is dead, and
    # the composition must carry the host's floor to the foundation that enforces it
    assert "$29" not in seen_by_brain


async def test_should_retrieve_the_passage_that_answers_a_natural_question(tmp_path):
    # given
    knowledge_service = _knowledge_over(
        tmp_path / "knowledge",
        ("refunds.md",
            "Refund policy. Enterprise customers may request a refund within 90 days of "
            "purchase. Refunds are issued to the original payment method."),
        ("shipping.md",
            "Shipping policy. Orders ship within two business days. Expedited shipping is "
            "available for an additional fee."),
        ("holidays.md",
            "The office is closed on public holidays and reopens the next business day."))

    # when: a question, phrased as a person would phrase it
    actual_passages = await knowledge_service.retrieve_knowledge(
        query="what is our refund policy for enterprise customers?")

    # then
    assert len(actual_passages) == 1
    assert "90 days" in actual_passages[0]
