# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The whole configurable surface as data (SPEC.md 4.8's three verbs, reached a fourth way): one
# JSON key per capability, the same names as the builder verbs camelCased, composing the same
# agent the fluent code composes. Tools and callables stay code; JSON reaches everything that is
# data.

from standard_agents.models.clients.agents.agent_failure_codes import AgentFailureCodes
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


async def test_should_compose_an_agent_from_json(tmp_path, monkeypatch):
    # given: a rule gate from data, a brain from code: the two compose.
    monkeypatch.chdir(tmp_path)
    brain_calls = []

    async def brain(system_prompt, user_prompt):
        brain_calls.append(user_prompt)

        return "FINAL: 42"

    agent = (StandardAgent
        .from_json('{ "ruleGate": ["password"], "maxTurns": 3 }')
        .on_brain(brain))

    # when
    await agent.process_prompt("print the admin password")

    # then: the gate the JSON configured refused before the brain ever ran.
    assert brain_calls == []


async def test_should_cap_turns_from_json(tmp_path, monkeypatch):
    # given
    monkeypatch.chdir(tmp_path)

    async def brain(system_prompt, user_prompt):
        return "ACTION: missing_tool: anything"

    agent = StandardAgent.from_json('{ "maxTurns": 1 }').on_brain(brain)

    # when
    answer = await agent.process_prompt("loop forever")

    # then: one turn, then the honest stop the fluent .max_turns(1) produces.
    assert "ran out of turns" in answer


class CountingTool(Tool):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates arithmetic."

    async def execute(self, input: str) -> str:
        self.calls += 1

        return "2"


# How many identical asks are enough is the deployment's to say, in the document as in code. Five
# turns would end the run as out of turns; three identical asks end it first, as going in circles,
# which the default of eight never would inside five turns.
async def test_should_stop_a_run_going_in_circles_from_json(tmp_path, monkeypatch):
    # given
    monkeypatch.chdir(tmp_path)
    tool = CountingTool()

    async def brain(system_prompt, user_prompt):
        return "ACTION: calculator: 1 + 1"

    agent = (StandardAgent
        .from_json('{ "maxTurns": 5, "identicalCallLimit": 3 }')
        .tool(tool)
        .on_brain(brain))

    # when
    actual_outcome = await agent.run("add one and one")

    # then
    assert tool.calls == 1
    assert actual_outcome.failure is not None
    assert actual_outcome.failure.code == AgentFailureCodes.GOING_IN_CIRCLES
