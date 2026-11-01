# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The whole configurable surface as data (SPEC.md 4.8's three verbs, reached a fourth way): one
# JSON key per capability, the same names as the builder verbs camelCased, composing the same
# agent the fluent code composes. Tools and callables stay code; JSON reaches everything that is
# data.

from standard_agents.standard_agent import StandardAgent


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
