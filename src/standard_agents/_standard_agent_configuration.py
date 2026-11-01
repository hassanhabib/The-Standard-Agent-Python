# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The agent document: JSON read into the same verbs code calls (StandardAgent.from_json)."""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

from standard_agents.models.clients.agents.exceptions import (
    InvalidAgentApiUrlException,
    InvalidAgentBudgetException,
    InvalidAgentConfigurationException)

from standard_agents.models.brokers.agents.registered_agent import RegisteredAgent
from standard_agents.models.foundations.brains.redaction_rule import RedactionRule
from standard_agents.models.loggings.trace_verbosity import TraceVerbosity
from standard_agents.models.orchestrations.effects.permission_mode import PermissionMode
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel

if TYPE_CHECKING:
    from standard_agents.standard_agent import StandardAgent

_Named = TypeVar("_Named", bound=Enum)


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
    # One case per capability, named exactly as the builder verb it drives, camelCased: the parity
    # test feeds a document containing every key, so a verb added without a binding turns red
    # there.
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

        case "nativeBrain":
            agent.native_brain(
                value["apiUrl"],
                value.get("apiKey", ""),
                value["model"],
                temperature=value.get("temperature", 0.7),
                max_tokens=value.get("maxTokens", 1024))

        case "nativeBrainAnthropic":
            agent.native_brain_anthropic(
                value["apiKey"],
                value["model"],
                temperature=value.get("temperature", 0.7),
                max_tokens=value.get("maxTokens", 1024))

        case "skills" if isinstance(value, list):
            for source in value:
                agent.skills(source)

        case "skills":
            agent.skills(value)

        case "knowledge" if isinstance(value, dict):
            agent.knowledge(
                value["path"],
                pattern=value.get("pattern", "*.md"),
                max_results=value.get("maxResults", 3),
                min_score=value.get("minScore", 0.0))

        case "knowledge":
            agent.knowledge(value)

        case "memory":
            agent.memory(value)

        case "mcp" if isinstance(value, list):
            for server in value:
                _apply_mcp_server(agent, server)

        case "mcp":
            _apply_mcp_server(agent, value)

        case "agents" if isinstance(value, list):
            for member in value:
                _apply_fleet_member(agent, member, key)

        case "agents":
            agent.agents(value)

        case "gate":
            agent.gate(
                value["apiUrl"],
                value.get("apiKey", ""),
                value["model"],
                temperature=value.get("temperature", 0.0),
                max_tokens=value.get("maxTokens", 16),
                timeout_seconds=value.get("timeoutSeconds", 30))

        case "ruleGate":
            agent.rule_gate(*value)

        case "judge":
            agent.judge(
                value["apiUrl"],
                value.get("apiKey", ""),
                value["model"],
                temperature=value.get("temperature", 0.0),
                max_tokens=value.get("maxTokens", 16),
                timeout_seconds=value.get("timeoutSeconds", 30))

        case "ruleJudge":
            agent.rule_judge(*value)

        # The contract is itself a JSON schema, so it rides embedded rather than as an escaped
        # string a form author would have to hand-quote.
        case "contract":
            agent.contract("{}" if value is None else json.dumps(value, separators=(",", ":")))

        case "constitution":
            agent.constitution(value)

        case "consumption":
            agent.consumption(value)

        case "redact" if isinstance(value, dict):
            agent.redact(*(
                RedactionRule(label=rule["label"], pattern=rule["pattern"])
                for rule in value["rules"]))

        case "redact" if value:
            agent.redact()

        case "redact":
            pass

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

        case "allowTools":
            agent.allow_tools(*value)

        case "permissions":
            agent.permissions(_named(PermissionMode, value, key))

        case "risk":
            for level_name, tool_names in value.items():
                agent.risk(_named(RiskLevel, level_name, key), *tool_names)

        case "requireApproval":
            agent.require_approval(*value)

        case "logTo" if isinstance(value, dict):
            agent.log_to(
                value["path"],
                verbosity=_named(TraceVerbosity, value.get("verbosity", "Full"), key))

        case "logTo":
            agent.log_to(value)

        case "audit":
            agent.audit(value)

        case "telemetry" if isinstance(value, str):
            agent.telemetry(agent_name=value)

        case "telemetry" if value:
            agent.telemetry()

        case "telemetry":
            pass

        case "sessions" if isinstance(value, dict):
            agent.sessions(value["path"], max_history_turns=value.get("maxHistoryTurns", 20))

        case "sessions":
            agent.sessions(value)

        case "effectLedger":
            agent.effect_ledger(value)

        case "screenToolOutput" if value:
            agent.screen_tool_output()

        case "screenToolOutput":
            pass

        case "budget":
            _apply_budget(agent, value)

        case "usage":
            agent.usage(characters_per_token=value.get("charactersPerToken", 4.0))

        case "resilience" if isinstance(value, dict):
            agent.resilience(retries=value.get("retries", 3))

        case "resilience":
            agent.resilience(retries=value)

        case "compensateOnFailure" if value:
            agent.compensate_on_failure()

        case "compensateOnFailure":
            pass

        case _:
            raise InvalidAgentConfigurationException(
                message=(
                    f"Unknown configuration key '{key}'. A key this agent does not know is a "
                    + "control you believe is on and is not, so it refuses to compose. "
                    + "The keys are the builder verbs, camelCased \u2014 see docs/how-to.md."))


def _apply_fleet_member(agent: StandardAgent, member: Any, key: str) -> None:
    # A fleet member is a path when the agents live beside the process (a folder of agent
    # documents), an object when the agent rides inline: the same document from_json composes,
    # identity included, because the document IS the agent. An inline member must be named: a
    # handoff calls agents by name, and a nameless agent is one the brain could never call.
    if not isinstance(member, dict):
        agent.agents(member)

        return

    composed = type(agent).from_json(json.dumps(member))

    if not composed.name or composed.name.isspace():
        raise InvalidAgentConfigurationException(
            message=(
                f"An inline '{key}' entry needs a 'name' \u2014 a handoff calls agents by "
                + "name."))

    registered_agents = [RegisteredAgent(composed.name, composed.description, composed)]

    async def select_agents() -> list[RegisteredAgent]:
        return registered_agents

    agent.on_agents(select_agents)


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


def _apply_mcp_server(agent: StandardAgent, server: Any) -> None:
    # A server is a URL when it needs nothing else, an object when it carries auth: an API key in
    # a named header, or a bearer token (an OAuth access token or PAT). A refresh-flow token is
    # code (a callable) and arrives through use_mcp, never through the document.
    if isinstance(server, dict) and "command" in server:
        agent.mcp_process(
            server["command"],
            arguments=_mcp_arguments(server),
            environment_variables=_mcp_environment_variables(server),
            working_directory=server.get("workingDirectory"),
            timeout_seconds=server.get("timeoutSeconds", 30))

        return

    if isinstance(server, dict):
        agent.mcp(
            server["endpointUrl"],
            relative_url=server.get("relativeUrl", ""),
            timeout_seconds=server.get("timeoutSeconds", 30),
            bearer_token=server.get("bearerToken"),
            api_key=server.get("apiKey"),
            api_key_header=server.get("apiKeyHeader", "X-Api-Key"))

        return

    agent.mcp(server)



# A process server takes the builder's words, or the words MCP clients' own configuration files
# already use, so a server's published setup pastes in unchanged.
def _mcp_arguments(server: dict[str, Any]) -> list[str]:
    arguments = server.get("arguments")

    if arguments is None:
        arguments = server.get("args")

    return [] if arguments is None else list(arguments)


def _mcp_environment_variables(server: dict[str, Any]) -> dict[str, str] | None:
    environment_variables = server.get("environmentVariables")

    if environment_variables is None:
        environment_variables = server.get("env")

    return None if environment_variables is None else dict(environment_variables)

def _named(enumeration: type[_Named], name: str, key: str) -> _Named:
    """The member a name means, as .NET's Enum.TryParse reads it: whatever the case."""
    for member in enumeration:
        if _csharp_name(member).lower() == name.strip().lower():
            return member

    raise InvalidAgentConfigurationException(
        message=(
            f"'{key}' does not accept '{name}'. It accepts: "
            + ", ".join(_csharp_name(member) for member in enumeration) + "."))


def _csharp_name(member: Enum) -> str:
    """The member's name as the document and the C# spell it: IRREVERSIBLE is Irreversible."""
    return "".join(word.capitalize() for word in member.name.split("_"))
