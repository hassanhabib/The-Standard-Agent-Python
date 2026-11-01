# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Found in the 2026-09-04 principal review (F-09): the agent's primary member was a string in and
# a string out, and its outcome-reporting members defaulted to "the run answered". An agent that
# implemented only the string door had every held or refused run reported to a host or an outer
# agent as an answer. The request-rich members are the contract now; the string members are
# adapters over them, so an adapter can never fabricate a status.

from standard_agents.agent import Agent
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus

HELD_RESULT = "waiting on an authority"


class HoldingAgent(Agent):
    """An agent written against the contract alone, the two request-rich primaries, whose runs
    are held: exactly the case an adapter must not turn into an answer."""

    async def run_request(self, request, *, cancellation=None):
        return AgentOutcome(result=HELD_RESULT, status=AgentStatus.AWAITING_APPROVAL)

    async def stream_request(self, request, *, cancellation=None):
        yield AgentStreamEvent(AgentStreamEventType.STATUS, HELD_RESULT)


async def test_should_report_a_held_run_truthfully_through_the_string_run_adapters():
    # given
    agent = HoldingAgent()

    expected_outcome = AgentOutcome(result=HELD_RESULT, status=AgentStatus.AWAITING_APPROVAL)

    # when
    actual_outcome = await agent.run("wire the money")
    actual_stoppable_outcome = await agent.run("wire the money", cancellation=None)
    actual_answer = await agent.process_prompt("wire the money")

    # then: the adapters carried what the run reported, not what they assumed
    assert actual_outcome == expected_outcome
    assert actual_stoppable_outcome == expected_outcome
    assert actual_answer == HELD_RESULT
