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


# The fix above was first applied to one branch of one path. The root cause, Interpret copying the
# incoming status forward, has three exits. Exit two is the streamed path: a streamed draft
# rejected once and accepted on revision must not spin to the cap either.
async def test_should_deliver_a_draft_that_passes_on_revision_when_streamed():
    # given: the same judge as the batched test above
    evaluate, judged = _judge_rejecting_once()

    agent = (StandardAgent()
        .on_brain(_forty_two)
        .on_judge(evaluate)
        .max_turns(4))

    # when
    responses = [
        stream_event.content
        async for stream_event in agent.process_prompt_stream("what is the answer")
        if stream_event.type == AgentStreamEventType.RESPONSE]

    # then: a control a caller can step around by changing method is not a control
    assert "forty two" in "".join(responses)
    assert len(judged) == 2


class _RecordingTool(Tool):
    def __init__(self) -> None:
        self.execution_count = 0

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates arithmetic."

    async def execute(self, input: str) -> str:
        self.execution_count += 1

        return "4183"


# Exit three: the tool-call branch. A model told its draft was rejected may consult a tool before
# drafting again, and a stale revising status carried out of Decision would skip Direction and
# swallow the call.
async def test_should_execute_a_tool_the_model_chooses_after_a_rejection():
    # given: reject the guess; the model then consults a tool and answers from it
    tool = _RecordingTool()
    evaluate, _ = _judge_rejecting_once()
    replies = iter([
        "FINAL: a guess",
        "ACTION: calculator: 47*89"])

    async def brain(system_prompt, user_prompt):
        return next(replies, "FINAL: the answer is 4183")

    agent = (StandardAgent()
        .tool(tool)
        .on_brain(brain)
        .on_judge(evaluate)
        .max_turns(5))

    # when
    actual_answer = await agent.process_prompt("what is 47*89")

    # then: a revision signal that swallows the act is a retry that cannot succeed that way
    assert tool.execution_count == 1
    assert actual_answer == "the answer is 4183"


# The other half, already covered and still true: a draft that never passes ends in a graceful
# refusal rather than an exception or an empty string.
async def test_should_refuse_when_no_draft_ever_passes():
    # given
    async def rejecting_judge(judge_rubric, draft_answer):
        return "0.0"

    agent = (StandardAgent()
        .on_brain(_forty_two)
        .on_judge(rejecting_judge)
        .max_turns(3))

    # when
    actual_answer = await agent.process_prompt("what is the answer")

    # then
    assert actual_answer == "I can't help with that at the moment."
