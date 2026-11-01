# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The whole configurable surface as data (SPEC.md 4.8's three verbs, reached a fourth way): one
# JSON key per capability, the same names as the builder verbs camelCased, composing the same
# agent the fluent code composes. Tools and callables stay code; JSON reaches everything that is
# data.

import itertools
import json
import os
import re
import sys

import pytest

from standard_agents.models.clients.agents.agent_failure_codes import AgentFailureCodes
from standard_agents.models.clients.agents.exceptions import (
    InvalidAgentApiUrlException,
    InvalidAgentBudgetException,
    InvalidAgentConfigurationException)
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool

STUDENTS_SERVER_PATH = os.path.join(os.path.dirname(__file__), "students_mcp_server.py")


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


# Citation is a deployment's decision (SPEC.md 4.2), so it is data: true cites with the default
# prefix, a string cites with that prefix. The knowledge itself is code here, the same way a tool
# is: a sourced broker is outside the document.
@pytest.mark.parametrize(("cite_knowledge", "expected_prefix"), [
    ("true", "Source: "),
    ('"Reference: "', "Reference: "),
])
async def test_should_cite_knowledge_from_json(
        tmp_path,
        monkeypatch,
        cite_knowledge,
        expected_prefix):

    # given
    monkeypatch.chdir(tmp_path)

    knowledge_results = [
        KnowledgeResult(
            text="Enterprise customers may request a refund within 90 days.",
            score=0.9,
            source="Refund Policy"),
    ]

    async def retrieve(query):
        return knowledge_results

    async def brain(system_prompt, user_prompt):
        return "FINAL: 90 days."

    agent = (StandardAgent
        .from_json('{ "citeKnowledge": ' + cite_knowledge + " }")
        .on_sourced_knowledge(retrieve)
        .on_brain(brain))

    # when
    actual_result = await agent.process_prompt("what is the refund window?")

    # then
    assert actual_result == f"90 days.\n\n{expected_prefix}Refund Policy"


# Identity is what makes an agent document registrable: the name a handoff calls, the description
# that advertises it. They ride in the document itself, so the file IS the agent: a registry
# needs nothing beside it.
def test_should_compose_agent_identity_from_json():
    # given . when
    agent = StandardAgent.from_json(
        '{ "name": "billing", "description": "Handles refunds and invoices." }')

    # then
    assert agent.name == "billing"
    assert agent.description == "Handles refunds and invoices."


def test_should_reject_an_unknown_configuration_key():
    # given . when
    with pytest.raises(InvalidAgentConfigurationException) as raised:
        StandardAgent.from_json('{ "buget": { "maxTokens": 50000 } }')

    # then: a typo'd key must not produce an unbounded agent that looks configured.
    assert "buget" in raised.value.message


def test_should_reject_a_nameless_inline_fleet_member():
    # given . when: an inline fleet member with no name is an agent no handoff could ever call,
    # so it refuses to compose rather than registering an unreachable agent.
    with pytest.raises(InvalidAgentConfigurationException) as raised:
        StandardAgent.from_json('{ "agents": [ { "maxTurns": 2 } ] }')

    # then
    assert re.search("agents.*name", raised.value.message)


# A dollar bound priced at zero per token is zero dollars forever: the document looks bounded and
# is not, so it refuses to compose rather than composing an agent whose cost budget can never trip
# (principal review 2026-09-04, F-01). The builder's own refusal rides along as the inner
# exception; the document-level message names the entries the author must fix.
def test_should_throw_invalid_agent_configuration_exception_on_from_json_if_cost_budget_has_no_rate():
    # given
    invalid_agent_budget_exception = InvalidAgentBudgetException(
        message=(
            "Invalid agent budget: a cost bound (maxCostUsd) needs a positive "
            + "costPerThousandTokens. Cost is the token count times that rate, so at "
            + "zero the bound can never trip. Pass your model's rate, or bound by "
            + "maxTokens instead."))

    expected_invalid_agent_configuration_exception = InvalidAgentConfigurationException(
        message=(
            "The 'budget' entry sets 'maxCostUsd' without a positive "
            + "'costPerThousandTokens'. Cost is priced off the token count times that "
            + "rate, so without it the spend is zero forever and the bound can never "
            + "trip. Add your model's rate, or bound by 'maxTokens' instead."),
        inner_exception=invalid_agent_budget_exception)

    # when
    with pytest.raises(InvalidAgentConfigurationException) as raised:
        StandardAgent.from_json('{ "budget": { "maxCostUsd": 0.25 } }')

    # then
    assert raised.value.same_exception_as(expected_invalid_agent_configuration_exception)


# The document reaches the same verb code does, so the same URL shape is refused, and the refusal
# names the entry, because the author is looking at a JSON file, not a stack trace.
def test_should_throw_invalid_agent_configuration_exception_on_from_json_if_brain_api_url_is_invalid():
    # given
    invalid_agent_api_url_exception = InvalidAgentApiUrlException(
        message=(
            "Invalid agent API URL. An endpoint is the base the route is appended to: an "
            + "absolute http(s) URL ending with '/', such as "
            + "https://api.peerllm.com/v1/, that does not name chat/completions "
            + "itself."))

    expected_invalid_agent_configuration_exception = InvalidAgentConfigurationException(
        message=(
            "The 'brain' entry's 'apiUrl' is not an endpoint base the route can be "
            + "appended to. " + invalid_agent_api_url_exception.message),
        inner_exception=invalid_agent_api_url_exception)

    # when
    with pytest.raises(InvalidAgentConfigurationException) as raised:
        StandardAgent.from_json(
            '{ "brain": { "apiUrl": "http://localhost:11434/v1/chat/completions", '
            + '"apiKey": "k", "model": "m" } }')

    # then
    assert raised.value.same_exception_as(expected_invalid_agent_configuration_exception)


def test_should_reject_malformed_configuration_json():
    # given . when . then
    with pytest.raises(InvalidAgentConfigurationException):
        StandardAgent.from_json("{ not json at all")


# The parity gate: every data-expressible capability, all in one document, must compose. A
# capability added to the builder without a JSON binding turns red here the moment its key is
# added below, and the key list below is part of the docs' contract.
def test_should_compose_every_data_expressible_capability_from_json():
    # given
    everything = r"""
    {
      "name": "concierge",
      "description": "Answers anything, hands off what it should not answer.",
      "brain": { "apiUrl": "https://api.peerllm.com/v1/", "apiKey": "k", "model": "LLooMA2.0",
                 "temperature": 0.2, "maxTokens": 512, "timeoutSeconds": 60 },
      "nativeBrain": { "apiUrl": "https://api.peerllm.com/v1/", "apiKey": "k", "model": "m" },
      "nativeBrainAnthropic": { "apiKey": "k", "model": "claude-sonnet-4-5" },
      "skills": ["Skills", "MoreSkills"],
      "knowledge": { "path": "Knowledge", "pattern": "*.md", "maxResults": 3, "minScore": 0.1 },
      "memory": "memory.txt",
      "mcp": [
        "https://mcp.example/",
        { "endpointUrl": "https://locked.example/", "timeoutSeconds": 20,
          "bearerToken": "token", "apiKey": "key", "apiKeyHeader": "X-Api-Key" }
      ],
      "agents": [
        "Fleet",
        { "name": "billing", "description": "Handles refunds and invoices.", "maxTurns": 2 }
      ],
      "gate": { "apiUrl": "https://api.peerllm.com/v1/", "apiKey": "k", "model": "m" },
      "ruleGate": ["password", "ssn"],
      "judge": { "apiUrl": "https://api.peerllm.com/v1/", "apiKey": "k", "model": "m" },
      "ruleJudge": ["Sources:"],
      "contract": { "type": "object", "required": ["amount"] },
      "constitution": "Constitution/ethics.md",
      "consumption": "Constitution/consuming-skills.md",
      "redact": { "rules": [ { "label": "TICKET", "pattern": "INC-\\d{6}" } ] },
      "maxTurns": 5,
      "allowTools": ["calculator", "write_file:/project/"],
      "permissions": "Ask",
      "risk": { "irreversible": ["wire_transfer"], "sensitive": ["write_file"] },
      "requireApproval": ["wire_transfer"],
      "logTo": { "path": "log.txt", "verbosity": "Natures" },
      "audit": "audit.jsonl",
      "telemetry": "form-built-agent",
      "sessions": { "path": "sessions", "maxHistoryTurns": 10 },
      "effectLedger": "ledger",
      "screenToolOutput": true,
      "budget": { "maxTokens": 50000, "maxCostUsd": 0.25,
                  "maxWallClockSeconds": 30, "costPerThousandTokens": 0.002 },
      "usage": { "charactersPerToken": 3.5 },
      "resilience": { "retries": 3 },
      "compensateOnFailure": true
    }
    """

    # when
    agent = StandardAgent.from_json(everything)

    # then
    assert agent is not None


async def test_should_start_an_mcp_server_process_from_json(tmp_path, monkeypatch):
    # given: a server entry that is a command rather than a URL, in the builder's words and in
    # the words MCP clients' own configuration files already use (args, env), so a server's
    # published setup pastes in unchanged
    monkeypatch.chdir(tmp_path)
    command = json.dumps(sys.executable)
    server_path = json.dumps(STUDENTS_SERVER_PATH)

    document = f"""
    {{
      "mcp": [
        {{ "command": {command}, "arguments": [{server_path}, "fall"],
           "environmentVariables": {{ "STUDENTS_SCHOOL": "Redmond High" }} }},
        {{ "command": {command}, "args": [{server_path}, "spring"],
           "env": {{ "STUDENTS_SCHOOL": "Kent Meridian" }}, "timeoutSeconds": 20 }}
      ]
    }}
    """

    observed_prompts = []
    turns = itertools.count(1)

    async def brain(system_prompt, user_prompt):
        if next(turns) == 1:
            return "ACTION: find_student: 1"

        observed_prompts.append(user_prompt)

        return "FINAL: done"

    agent = StandardAgent.from_json(document).on_brain(brain)

    # when
    await agent.process_prompt("who is student 1?")

    # then: the first-registered process owns the name, started as the document said
    assert "student 1 is Hassan, at Redmond High, for the fall term" in observed_prompts[-1]


def test_should_compose_multiple_integrations_from_json():
    # given: integrations are plural in the document the same way they are in code: a form adds
    # a row, the agent gains a source.
    integrations = """
    {
      "skills": ["Skills", "Compliance/Skills"],
      "mcp": [
        "https://tools.example/",
        { "endpointUrl": "https://internal.example/", "apiKey": "psk-1" }
      ]
    }
    """

    # when
    agent = StandardAgent.from_json(integrations)

    # then
    assert agent is not None
