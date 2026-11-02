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

from standard_agents._standard_agent_schema import document_property_names
from standard_agents.models.brokers.agents.registered_agent import RegisteredAgent
from standard_agents.models.foundations.brains.redaction_rule import RedactionRule
from standard_agents.models.loggings.trace_verbosity import TraceVerbosity
from standard_agents.models.orchestrations.effects.permission_mode import PermissionMode
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel

if TYPE_CHECKING:
    from standard_agents.standard_agent import StandardAgent

_Named = TypeVar("_Named", bound=Enum)
_Limit = TypeVar("_Limit", int, Decimal, timedelta)


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
            agent.identity(_text(value, key), description=agent.description)

        case "description":
            agent.identity(agent.name, description=_text(value, key))

        case "brain":
            _shaped(value, key)

            agent.brain(
                _text_property(value, key, "apiUrl"),
                _text_property(value, key, "apiKey", fallback=""),
                _text_property(value, key, "model"),
                temperature=_number(value, key, "temperature", 0.7),
                max_tokens=_positive_whole(value, key, "maxTokens", 1024),
                timeout_seconds=_positive_whole(value, key, "timeoutSeconds", 120))

        case "nativeBrain":
            _shaped(value, key)

            agent.native_brain(
                _text_property(value, key, "apiUrl"),
                _text_property(value, key, "apiKey", fallback=""),
                _text_property(value, key, "model"),
                temperature=_number(value, key, "temperature", 0.7),
                max_tokens=_positive_whole(value, key, "maxTokens", 1024))

        case "nativeBrainAnthropic":
            _shaped(value, key)

            agent.native_brain_anthropic(
                _text_property(value, key, "apiKey"),
                _text_property(value, key, "model"),
                temperature=_number(value, key, "temperature", 0.7),
                max_tokens=_positive_whole(value, key, "maxTokens", 1024))

        case "skills" if isinstance(value, list):
            for source in _listed(value, key):
                agent.skills(_text(source, key))

        case "skills":
            agent.skills(_text(value, key))

        case "knowledge" if isinstance(value, dict):
            _shaped(value, key)

            agent.knowledge(
                _text_property(value, key, "path"),
                pattern=_text_property(value, key, "pattern", fallback="*.md"),
                max_results=_positive_whole(value, key, "maxResults", 3),
                min_score=_number(value, key, "minScore", 0.0))

        case "knowledge":
            agent.knowledge(_text(value, key))

        # A document that wants no memory says so with one key: a hosted agent is the whole
        # document, and a hosted memory is one memory for every caller.
        case "memory" if isinstance(value, bool):
            if not value:
                agent.without_memory()

        case "memory":
            agent.memory(_text(value, key))

        case "mcp" if isinstance(value, list):
            for server in _listed(value, key):
                _apply_mcp_server(agent, server, key)

        case "mcp":
            _apply_mcp_server(agent, value, key)

        case "agents" if isinstance(value, list):
            for member in _listed(value, key):
                _apply_fleet_member(agent, member, key)

        case "agents":
            agent.agents(_text(value, key))

        case "gate":
            _shaped(value, key)

            agent.gate(
                _text_property(value, key, "apiUrl"),
                _text_property(value, key, "apiKey", fallback=""),
                _text_property(value, key, "model"),
                temperature=_number(value, key, "temperature", 0.0),
                max_tokens=_positive_whole(value, key, "maxTokens", 16),
                timeout_seconds=_positive_whole(value, key, "timeoutSeconds", 30))

        case "ruleGate":
            agent.rule_gate(*_listed_texts(value, key))

        case "judge":
            _shaped(value, key)

            agent.judge(
                _text_property(value, key, "apiUrl"),
                _text_property(value, key, "apiKey", fallback=""),
                _text_property(value, key, "model"),
                temperature=_number(value, key, "temperature", 0.0),
                max_tokens=_positive_whole(value, key, "maxTokens", 16),
                timeout_seconds=_positive_whole(value, key, "timeoutSeconds", 30))

        case "ruleJudge":
            agent.rule_judge(*_listed_texts(value, key))

        # The contract is itself a JSON schema, so it rides embedded rather than as an escaped
        # string a form author would have to hand-quote.
        case "contract":
            agent.contract("{}" if value is None else json.dumps(value, separators=(",", ":")))

        case "constitution":
            agent.constitution(_text(value, key))

        case "consumption":
            agent.consumption(_text(value, key))

        case "redact" if isinstance(value, dict):
            _shaped(value, key)

            agent.redact(*(
                RedactionRule(
                    label=_text_property(
                        _shaped(rule, "redact.rules"), "redact.rules", "label"),
                    pattern=_text_property(rule, "redact.rules", "pattern"))
                for rule in _listed(value.get("rules"), "redact.rules")))

        case "redact" if _truth(value, key):
            agent.redact()

        case "redact":
            pass

        case "maxTurns":
            agent.max_turns(_positive(_whole(value, key), key))

        case "identicalCallLimit":
            agent.identical_call_limit(_positive(_whole(value, key), key))

        # true or false is the deployment's decision; text is that decision made with the words
        # each citation line starts with (SPEC.md 4.2).
        case "citeKnowledge" if isinstance(value, str):
            agent.cite_knowledge(prefix=_citation_prefix(value, key))

        case "citeKnowledge" if isinstance(value, bool):
            agent.cite_knowledge(cite=value)

        case "citeKnowledge":
            raise InvalidAgentConfigurationException(message=_citation_refusal(key))

        case "allowTools":
            agent.allow_tools(*_texts(value, key))

        case "permissions":
            agent.permissions(_named(PermissionMode, _text(value, key), key))

        case "risk":
            for level_name, tool_names in _listed_entries(value, key).items():
                agent.risk(_named(RiskLevel, level_name, key), *_texts(tool_names, key))

        case "requireApproval":
            agent.require_approval(*_listed_texts(value, key))

        case "logTo" if isinstance(value, dict):
            _shaped(value, key)

            agent.log_to(
                _text_property(value, key, "path"),
                verbosity=_named(
                    TraceVerbosity,
                    _text_property(value, key, "verbosity", fallback="Full"),
                    key))

        case "logTo":
            agent.log_to(_text(value, key))

        case "audit":
            agent.audit(_text(value, key))

        case "auditPayloads" if _truth(value, key):
            agent.audit_payloads()

        case "auditPayloads":
            pass

        case "telemetry" if isinstance(value, str):
            agent.telemetry(agent_name=_text(value, key))

        case "telemetry" if _truth(value, key):
            agent.telemetry()

        case "telemetry":
            pass

        case "sessions" if isinstance(value, dict):
            _shaped(value, key)

            agent.sessions(
                _text_property(value, key, "path"),
                max_history_turns=_positive_whole(value, key, "maxHistoryTurns", 20))

        case "sessions":
            agent.sessions(_text(value, key))

        case "effectLedger":
            agent.effect_ledger(_text(value, key))

        case "effectLeaseSeconds":
            agent.effect_lease(
                timedelta(seconds=_positive_number(_number_value(value, key), key)))

        case "screenToolOutput" if _truth(value, key):
            agent.screen_tool_output()

        case "screenToolOutput":
            pass

        case "budget":
            _apply_budget(agent, value)

        case "usage":
            _shaped(value, key)

            agent.usage(
                characters_per_token=_positive_number(
                    _number(value, key, "charactersPerToken", 4.0),
                    f"{key}.charactersPerToken"))

        case "resilience" if isinstance(value, dict):
            _shaped(value, key)

            agent.resilience(
                retries=_non_negative(
                    _whole_property(value, key, "retries", 3),
                    f"{key}.retries"))

        case "resilience":
            agent.resilience(retries=_non_negative(_whole(value, key), key))

        case "compensateOnFailure" if _truth(value, key):
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
        agent.agents(_text(member, key))

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
    _shaped(budget, "budget")

    key = "budget"

    try:
        agent.budget(
            max_tokens=_positive(
                _optional_whole(budget, key, "maxTokens"),
                f"{key}.maxTokens"),
            max_cost_usd=_positive(
                _optional_money(budget, key, "maxCostUsd"),
                f"{key}.maxCostUsd"),
            max_wall_clock=_positive(
                _optional_seconds(budget, key, "maxWallClockSeconds"),
                f"{key}.maxWallClockSeconds"),
            cost_per_thousand_tokens=_non_negative(
                _money(budget, key, "costPerThousandTokens"),
                f"{key}.costPerThousandTokens"))
    except InvalidAgentBudgetException as invalid_agent_budget_exception:
        raise InvalidAgentConfigurationException(
            message=(
                "The 'budget' entry sets 'maxCostUsd' without a positive "
                + "'costPerThousandTokens'. Cost is priced off the token count times that "
                + "rate, so without it the spend is zero forever and the bound can never "
                + "trip. Add your model's rate, or bound by 'maxTokens' instead."),
            inner_exception=invalid_agent_budget_exception)


def _apply_mcp_server(agent: StandardAgent, server: Any, key: str) -> None:
    # A server is a URL when it needs nothing else, an object when it carries auth: an API key in
    # a named header, or a bearer token (an OAuth access token or PAT). A refresh-flow token is
    # code (a callable) and arrives through use_mcp, never through the document.
    if isinstance(server, dict) and "command" in server:
        _shaped(server, key)

        agent.mcp_process(
            _text_property(server, key, "command"),
            arguments=_mcp_arguments(server, key),
            environment_variables=_mcp_environment_variables(server, key),
            working_directory=_optional_text(server, "workingDirectory"),
            timeout_seconds=_positive_whole(server, key, "timeoutSeconds", 30))

        return

    if isinstance(server, dict):
        _shaped(server, key)

        agent.mcp(
            _text_property(server, key, "endpointUrl"),
            relative_url=_text_property(server, key, "relativeUrl", fallback=""),
            timeout_seconds=_positive_whole(server, key, "timeoutSeconds", 30),
            bearer_token=_optional_text(server, "bearerToken"),
            api_key=_optional_text(server, "apiKey"),
            api_key_header=_text_property(server, key, "apiKeyHeader", fallback="X-Api-Key"))

        return

    agent.mcp(_text(server, key))



# A process server takes the builder's words, or the words MCP clients' own configuration files
# already use, so a server's published setup pastes in unchanged.
def _mcp_arguments(server: dict[str, Any], key: str) -> list[str]:
    arguments = server.get("arguments")

    if arguments is None:
        arguments = server.get("args")

    if arguments is None:
        return []

    if not isinstance(arguments, list):
        raise InvalidAgentConfigurationException(message=f"'{key}' arguments must be an array.")

    return [_text(argument, key) for argument in arguments]


def _mcp_environment_variables(server: dict[str, Any], key: str) -> dict[str, str] | None:
    environment_variables = server.get("environmentVariables")

    if environment_variables is None:
        environment_variables = server.get("env")

    if environment_variables is None:
        return None

    if not isinstance(environment_variables, dict):
        raise InvalidAgentConfigurationException(
            message=f"'{key}' environment variables must be an object.")

    return {name: _text(value, key) for name, value in environment_variables.items()}


def _shaped(node: Any, key: str) -> dict[str, Any]:
    """A section, once its shape is checked against the schema's table (F-24).

    It must be an object, and every key in it must be one the section accepts. A nested typo
    used to be ignored, which is a control the author believes is on and is not, the same
    failure the top-level unknown-key refusal exists to prevent.
    """
    if not isinstance(node, dict):
        raise InvalidAgentConfigurationException(message=f"'{key}' must be an object.")

    properties = document_property_names(key)

    for document_property in node:
        if document_property not in properties:
            raise InvalidAgentConfigurationException(
                message=(
                    f"'{key}' does not accept '{document_property}'. It accepts: "
                    + ", ".join(properties) + "."))

    return node


def _text(node: Any, key: str) -> str:
    if not isinstance(node, str):
        raise InvalidAgentConfigurationException(message=f"'{key}' must be a string.")

    return node


def _text_property(
        node: Any,
        key: str,
        document_property: str,
        fallback: str | None = None) -> str:

    value = node.get(document_property) if isinstance(node, dict) else None

    if value is None:
        if fallback is None:
            raise InvalidAgentConfigurationException(
                message=f"'{key}' needs a '{document_property}'.")

        return fallback

    if not isinstance(value, str):
        raise InvalidAgentConfigurationException(
            message=f"'{key}.{document_property}' must be a string.")

    return value


def _optional_text(node: Any, document_property: str) -> str | None:
    value = node.get(document_property) if isinstance(node, dict) else None

    if value is None or isinstance(value, str):
        return value

    # Not a document refusal in the C# either: GetValue<string> on a value of another kind
    # throws InvalidOperationException, which is a RuntimeError here.
    raise RuntimeError(
        "The requested operation requires an element of type 'String', but the target element "
        + f"has type '{_kind_of(value)}'.")


def _texts(node: Any, key: str) -> list[str]:
    if not isinstance(node, list):
        raise InvalidAgentConfigurationException(message=f"'{key}' must be an array.")

    return [_text(item, key) for item in node]


def _listed_texts(node: Any, key: str) -> list[str]:
    return [_text(item, key) for item in _listed(node, key)]


def _truth(node: Any, key: str) -> bool:
    if not isinstance(node, bool):
        raise InvalidAgentConfigurationException(message=f"'{key}' must be true or false.")

    return node


def _kind_of(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"

    if isinstance(value, (int, float)):
        return "Number"

    return "Array" if isinstance(value, list) else "Object"


def _listed(node: Any, key: str) -> list[Any]:
    # A control that lists nothing is not a control: a gate with no rules, an approval list with
    # no tools, a fleet with no agents all read as on and do nothing.
    if not isinstance(node, list):
        raise InvalidAgentConfigurationException(message=f"'{key}' must be an array.")

    if not node:
        raise InvalidAgentConfigurationException(message=_lists_nothing(key))

    return node


def _listed_entries(node: Any, key: str) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise InvalidAgentConfigurationException(message=f"'{key}' must be an object.")

    if not node:
        raise InvalidAgentConfigurationException(message=_lists_nothing(key))

    return node


def _lists_nothing(key: str) -> str:
    return (
        f"'{key}' lists nothing. A control that lists nothing is not a control: remove the "
        + "key, or list what it should hold.")

def _citation_refusal(key: str) -> str:
    return f"'{key}' must be true, false, or the text each citation line starts with."


def _citation_prefix(prefix: str, key: str) -> str:
    if not prefix or prefix.isspace():
        raise InvalidAgentConfigurationException(message=_citation_refusal(key))

    return prefix


# A limit of zero or less composes as if it were set and never binds (or, in max_turns' case, is
# quietly clamped). The document refuses it by name instead.
def _positive(value: _Limit | None, name: str) -> _Limit | None:
    if value is None or value > _zero_of(value):
        return value

    raise InvalidAgentConfigurationException(message=f"'{name}' must be a positive number.")


def _positive_number(value: float, name: str) -> float:
    if value > 0:
        return value

    raise InvalidAgentConfigurationException(message=f"'{name}' must be a positive number.")


def _non_negative(value: _Limit, name: str) -> _Limit:
    if value >= _zero_of(value):
        return value

    raise InvalidAgentConfigurationException(
        message=f"'{name}' must be zero or a positive number.")


def _positive_whole(node: Any, key: str, document_property: str, fallback: int) -> int:
    return _positive(
        _whole_property(node, key, document_property, fallback),
        f"{key}.{document_property}")


def _zero_of(value: int | Decimal | timedelta) -> int | Decimal | timedelta:
    return timedelta(0) if isinstance(value, timedelta) else 0


# Numbers are read as numbers or refused by name; a string where a number belongs used to surface
# as a runtime exception with no entry named, or fall through to a default.
def _number_node(node: Any, key: str, document_property: str) -> int | float | None:
    value = node.get(document_property) if isinstance(node, dict) else None

    if value is None:
        return None

    if not _is_number(value):
        raise InvalidAgentConfigurationException(
            message=f"'{key}.{document_property}' must be a number.")

    return value


def _number(node: Any, key: str, document_property: str, fallback: float) -> float:
    value = _number_node(node, key, document_property)

    return fallback if value is None else float(value)


def _number_value(node: Any, key: str) -> float:
    if not _is_number(node):
        raise InvalidAgentConfigurationException(message=f"'{key}' must be a number.")

    return float(node)


def _whole(node: Any, key: str) -> int:
    if not _is_number(node):
        raise InvalidAgentConfigurationException(message=f"'{key}' must be a number.")

    return _as_int32(node)


def _whole_property(node: Any, key: str, document_property: str, fallback: int) -> int:
    value = _number_node(node, key, document_property)

    return fallback if value is None else _as_int32(value)


def _optional_whole(node: Any, key: str, document_property: str) -> int | None:
    value = _number_node(node, key, document_property)

    return None if value is None else _as_int32(value)


def _optional_money(node: Any, key: str, document_property: str) -> Decimal | None:
    value = _number_node(node, key, document_property)

    return None if value is None else Decimal(str(value))


def _money(node: Any, key: str, document_property: str) -> Decimal:
    value = _optional_money(node, key, document_property)

    return Decimal(0) if value is None else value


def _optional_seconds(node: Any, key: str, document_property: str) -> timedelta | None:
    value = _number_node(node, key, document_property)

    return None if value is None else timedelta(seconds=value)


def _is_number(value: Any) -> bool:
    # JSON true and false are not numbers, though Python counts bool as int.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_int32(value: int | float) -> int:
    # A number that is not a whole Int32 (3.5, 1e2, 2^31) is refused as .NET's GetValue<int>
    # refuses it: a FormatException, which is a ValueError here, not a document refusal.
    if isinstance(value, float) or not -2**31 <= value < 2**31:
        raise ValueError(
            "Either the JSON value is not in a supported format, or is out of bounds for an "
            + "Int32.")

    return value


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
