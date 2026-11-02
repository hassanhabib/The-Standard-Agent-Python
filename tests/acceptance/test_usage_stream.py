# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Usage, as it is spent (SPEC.md 4.14.1).

The loop has always counted what a run spends, because the budget cannot bound what it does not
count, and it kept the count to itself: somebody watching a run could read a clock and nothing
else. A local model thinking for four minutes and a paid one spending forty thousand tokens
looked the same until each of them ended.

So after every model call the stream says what the run has spent so far, the same count the
budget reads, marked estimated where nobody reported it.
"""

import pytest

from standard_agents.brokers.usages.usage_broker import UsageBroker
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


@pytest.fixture(autouse=True)
def _in_a_scratch_directory(tmp_path, monkeypatch):
    # The default memory file and knowledge folder resolve against the working directory.
    monkeypatch.chdir(tmp_path)


class _ScriptedTool(Tool):
    def __init__(self, name: str, output: str) -> None:
        self._name = name
        self._output = output

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "A scripted tool."

    async def execute(self, input: str) -> str:
        return self._output


class _FlatUsageBroker(UsageBroker):
    """Every text the same size, so every call costs the same and a running total is a count of
    calls.

    With the real estimate the second call always costs more than the first, because it carries
    the first one's result, and a stream reporting each call's own figure would grow just the
    same.
    """

    async def count_tokens(self, text: str) -> int:
        return 0 if not text else 10


async def _drain(agent: StandardAgent, prompt: str) -> list[AgentStreamEvent]:
    return [stream_event async for stream_event in agent.process_prompt_stream(prompt)]


async def test_should_say_what_the_run_has_spent_after_every_model_call():
    # given
    calls = 0

    async def brain(system_prompt, user_prompt):
        nonlocal calls
        calls += 1

        return "ACTION: calculator: 2+2" if calls == 1 else "FINAL: 4"

    agent = (StandardAgent()
        .on_brain(brain)
        .tool(_ScriptedTool("calculator", "4"))
        .use_usage(_FlatUsageBroker()))

    # when
    events = await _drain(agent, "what is 2+2?")

    # then
    usages = [
        stream_event
        for stream_event in events
        if stream_event.type is AgentStreamEventType.USAGE]

    assert len(usages) == calls, (
        "one model call to act and one to answer is two things spent, and somebody watching is "
        "owed each of them as it happens")

    assert usages[0].usage.total_tokens > 0

    assert usages[1].usage.total_tokens == usages[0].usage.total_tokens * 2, (
        "it is what the run has spent so far rather than what the last call cost, so a consumer "
        "that missed an event still reads the right number from the next")

    assert all(usage.content == str(usage.usage.total_tokens) for usage in usages), (
        "a consumer that reads only the text still reads the number")

    assert all(usage.usage.is_estimated for usage in usages), (
        "a brain that reports nothing was counted here, and an estimate presented as a "
        "measurement is the one thing SPEC.md 3.4 forbids outright")

    answer = "".join(
        stream_event.content
        for stream_event in events
        if stream_event.type is AgentStreamEventType.RESPONSE)

    assert answer == "4", "what a run spent is not part of what it answered"


async def test_should_count_the_draft_that_was_sent_back():
    # given
    judged = 0

    async def brain(system_prompt, user_prompt):
        return "FINAL: forty two"

    async def judge(judge_rubric, draft_answer):
        nonlocal judged
        judged += 1

        return "0.0" if judged == 1 else "1.0"

    agent = (StandardAgent()
        .on_brain(brain)
        .on_judge(judge)
        .max_turns(4))

    # when
    events = await _drain(agent, "what is the answer")

    # then
    usage_count = sum(
        1 for stream_event in events if stream_event.type is AgentStreamEventType.USAGE)

    assert usage_count == 2, (
        "a draft the Judge sent back was still written, and the tokens it took were spent "
        "whether or not anybody reads it")
