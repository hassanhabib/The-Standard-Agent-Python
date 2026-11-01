# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The decision log's three access modes (SPEC.md 4.8): Local is .audit(path) and is covered by
# the acceptance suite, since a file sink is only interesting end to end. External and Custom are
# covered here, where the sink can be observed directly.

from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.audits.audit_broker import AuditBroker
from standard_agents.standard_agent import StandardAgent


@pytest.fixture
def answering_agent(create_skill_broker, empty_memory_broker, empty_knowledge_broker):
    async def brain(system_prompt, user_prompt):
        return "FINAL: 42"

    return (StandardAgent()
        .use_skills(create_skill_broker())
        .use_memory(empty_memory_broker)
        .use_knowledge(empty_knowledge_broker)
        .on_brain(brain))


async def test_should_write_to_external_audit_broker_on_process_prompt(answering_agent):
    # given
    audit_broker = create_autospec(AuditBroker, instance=True)
    agent = answering_agent.use_audit(audit_broker)

    # when
    await agent.process_prompt(prompt="what is the answer?")

    # then
    assert audit_broker.write.await_count >= 1
