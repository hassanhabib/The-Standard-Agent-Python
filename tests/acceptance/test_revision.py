# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""A rejected draft is a re-think signal, not a fault: the loop retries within the turn budget
and refuses gracefully only when the answer still cannot pass.

The retry half was covered. The success half was not: every test asserted that a permanently
rejected draft ends in a refusal, and none asserted that a draft rejected once and then accepted
is the answer the caller receives. Interpret carried the incoming status forward, so a draft
accepted on the second pass was still marked revising when it left Decision, and the run
exhausted its turns refusing an answer that passed review.
"""

import pytest

from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


@pytest.fixture(autouse=True)
def _in_a_scratch_directory(tmp_path, monkeypatch):
    # The default memory file and knowledge folder resolve against the working directory.
    monkeypatch.chdir(tmp_path)


def _judge_rejecting_once():
    judged = []

    async def evaluate(judge_rubric, draft_answer):
        judged.append(draft_answer)

        return "0.0" if len(judged) == 1 else "1.0"

    return evaluate, judged


async def _forty_two(system_prompt, user_prompt):
    return "FINAL: forty two"


async def test_should_deliver_a_draft_that_passes_on_revision():
    # given: the Judge rejects the first draft and accepts every one after it
    evaluate, judged = _judge_rejecting_once()

    agent = (StandardAgent()
        .on_brain(_forty_two)
        .on_judge(evaluate)
        .max_turns(4))

    # when
    actual_answer = await agent.process_prompt("what is the answer")

    # then: a revision that passes review is an answer, and one rejection and one acceptance is
    # the whole exchange; anything more is the loop spinning after the answer was already good.
    assert actual_answer == "forty two"
    assert len(judged) == 2
