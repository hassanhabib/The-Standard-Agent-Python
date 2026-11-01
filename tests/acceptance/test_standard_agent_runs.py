# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import uuid

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.standard_agent import StandardAgent


# Acceptance: the whole agent, composed the way a user composes it, through the real brokers.
# Only the brain is a stand-in, because the brain is the one thing a test cannot own.
def create_random_string() -> str:
    return uuid.uuid4().hex


class TestStandardAgentRuns:
    def test_should_answer_through_the_brain(self) -> None:
        # given
        input_prompt = create_random_string()
        random_answer = create_random_string()
        expected_outcome = AgentOutcome(result=random_answer, status=AgentStatus.RESPONDED)

        async def brain(system_prompt: str, user_prompt: str) -> str:
            return f"FINAL: {random_answer}"

        agent = StandardAgent().on_brain(brain)

        # when
        actual_outcome = asyncio.run(agent.run(input_prompt))

        # then
        assert actual_outcome == expected_outcome
