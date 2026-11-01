# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The agent document: JSON read into the same verbs code calls (StandardAgent.from_json)."""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from standard_agents.models.clients.agents.exceptions import (
    InvalidAgentApiUrlException,
    InvalidAgentBudgetException,
    InvalidAgentConfigurationException)

if TYPE_CHECKING:
    from standard_agents.standard_agent import StandardAgent


def apply_document(agent: StandardAgent, document_json: str) -> None:
    """Configures the agent with every entry of the document, in the document's order."""
    document = _parse_document(document_json)

    for key, value in document.items():
        _apply_entry(agent, key, value)


def _parse_document(document_json: str) -> dict[str, Any]:
    try:
        parsed = json.loads(document_json)
    except json.JSONDecodeError as exception:
        raise InvalidAgentConfigurationException(
            message=f"The configuration is not valid JSON: {exception}")

    if not isinstance(parsed, dict):
        raise InvalidAgentConfigurationException(
            message="The configuration must be a JSON object with one key per capability.")

    return parsed


def _apply_entry(agent: StandardAgent, key: str, value: Any) -> None:
    # The document reaches the same verbs code does, so a verb's refusal is rewrapped into the
    # document's own exception naming the entry the author must fix (they are looking at a JSON
    # file, not a stack trace), with the verb's refusal preserved beneath it.
    try:
        _apply(agent, key, value)
    except InvalidAgentApiUrlException as invalid_agent_api_url_exception:
        raise InvalidAgentConfigurationException(
            message=(
                f"The '{key}' entry's 'apiUrl' is not an endpoint base the route can be "
                + "appended to. " + invalid_agent_api_url_exception.message),
            inner_exception=invalid_agent_api_url_exception)


def _apply(agent: StandardAgent, key: str, value: Any) -> None:
    match key:
        # Identity rides in the document, so the file IS the agent: a registry reads the name a
        # handoff calls and the description that advertises it from the same JSON that composes
        # it. Each key preserves the other, so their order cannot matter.
        case "name":
            agent.identity(value, description=agent.description)

        case "description":
            agent.identity(agent.name, description=value)

        case "brain":
            agent.brain(
                value["apiUrl"],
                value.get("apiKey", ""),
                value["model"],
                temperature=value.get("temperature", 0.7),
                max_tokens=value.get("maxTokens", 1024),
                timeout_seconds=value.get("timeoutSeconds", 120))

        case "ruleGate":
            agent.rule_gate(*value)

        case "maxTurns":
            agent.max_turns(value)

        case "identicalCallLimit":
            agent.identical_call_limit(value)

        # true or false is the deployment's decision; text is that decision made with the words
        # each citation line starts with (SPEC.md 4.2).
        case "citeKnowledge" if isinstance(value, str):
            agent.cite_knowledge(prefix=value)

        case "citeKnowledge":
            agent.cite_knowledge(cite=value)

        case "agents":
            for member in value:
                _apply_fleet_member(agent, member, key)

        case "budget":
            _apply_budget(agent, value)

        case _:
            raise InvalidAgentConfigurationException(
                message=(
                    f"Unknown configuration key '{key}'. A key this agent does not know is a "
                    + "control you believe is on and is not, so it refuses to compose. "
                    + "The keys are the builder verbs, camelCased \u2014 see docs/how-to.md."))


def _apply_fleet_member(agent: StandardAgent, member: Any, key: str) -> None:
    # A fleet member rides inline as the same document from_json composes, identity included,
    # because the document IS the agent. An inline member must be named: a handoff calls agents
    # by name, and a nameless agent is one the brain could never call.
    composed = type(agent).from_json(json.dumps(member))

    if not composed.name or composed.name.isspace():
        raise InvalidAgentConfigurationException(
            message=f"An inline '{key}' entry needs a 'name' \u2014 a handoff calls agents by name.")


def _apply_budget(agent: StandardAgent, budget: Any) -> None:
    # The builder is the one place the budget's rules live; the document reaches it through the
    # same verb code does. A refusal there is rewrapped into the document's own exception, naming
    # the entries the author must fix, with the builder's refusal preserved beneath it.
    max_wall_clock_seconds = budget.get("maxWallClockSeconds")
    max_cost_usd = budget.get("maxCostUsd")
    cost_per_thousand_tokens = budget.get("costPerThousandTokens")

    try:
        agent.budget(
            max_tokens=budget.get("maxTokens"),
            max_cost_usd=None if max_cost_usd is None else Decimal(str(max_cost_usd)),
            max_wall_clock=(
                None if max_wall_clock_seconds is None
                else timedelta(seconds=max_wall_clock_seconds)),
            cost_per_thousand_tokens=(
                Decimal(0) if cost_per_thousand_tokens is None
                else Decimal(str(cost_per_thousand_tokens))))
    except InvalidAgentBudgetException as invalid_agent_budget_exception:
        raise InvalidAgentConfigurationException(
            message=(
                "The 'budget' entry sets 'maxCostUsd' without a positive "
                + "'costPerThousandTokens'. Cost is priced off the token count times that "
                + "rate, so without it the spend is zero forever and the bound can never "
                + "trip. Add your model's rate, or bound by 'maxTokens' instead."),
            inner_exception=invalid_agent_budget_exception)
