# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The agent document, described once.

This table is what from_json validates a section's shape against and what the JSON Schema is
emitted from, so an editor's completion list and the builder's refusals cannot disagree: there is
one list (principal review 2026-09-04, F-24).
"""

from __future__ import annotations

from dataclasses import dataclass

_STRING = "string"
_NUMBER = "number"
_INTEGER = "integer"
_BOOLEAN = "boolean"
_OBJECT = "object"
_ARRAY = "array"


@dataclass(frozen=True)
class _DocumentProperty:
    """One property of an object section: its JSON kind, whether the section needs it, and
    whether it must be positive, the same rules the document switch enforces."""

    name: str
    kind: str
    required: bool = False
    positive: bool = False
    names: tuple[str, ...] | None = None


@dataclass(frozen=True)
class _DocumentSection:
    """One top-level key: the shapes it accepts, the properties of its object shape, the kind of
    its array items, the names of its enum shape, and an example that composes."""

    key: str
    description: str
    shapes: tuple[str, ...]
    example: str
    properties: tuple[_DocumentProperty, ...] | None = None
    items_kind: str | None = None
    items_section: str | None = None
    names: tuple[str, ...] | None = None
    boolean_must_be_false: bool = False


_ENDPOINT_PROPERTIES = (
    _DocumentProperty("apiUrl", _STRING, required=True),
    _DocumentProperty("apiKey", _STRING),
    _DocumentProperty("model", _STRING, required=True),
    _DocumentProperty("temperature", _NUMBER),
    _DocumentProperty("maxTokens", _INTEGER, positive=True),
    _DocumentProperty("timeoutSeconds", _INTEGER, positive=True),
)

_ENDPOINT_EXAMPLE = '{ "apiUrl": "http://localhost:11434/v1/", "model": "LLooMA2.0" }'

_DOCUMENT_SECTIONS = (
    _DocumentSection(
        "name", "The agent's name; a handoff calls agents by it.", (_STRING,),
        '"refund-desk"'),
    _DocumentSection(
        "description", "What the agent is for, as a registry advertises it.", (_STRING,),
        '"Handles refunds and invoices."'),
    _DocumentSection(
        "brain", "The text-protocol brain on an OpenAI-compatible endpoint.", (_OBJECT,),
        _ENDPOINT_EXAMPLE,
        properties=_ENDPOINT_PROPERTIES),
    _DocumentSection(
        "nativeBrain", "A native tool-calling brain on an OpenAI-compatible endpoint.",
        (_OBJECT,),
        _ENDPOINT_EXAMPLE,
        properties=tuple(
            endpoint_property for endpoint_property in _ENDPOINT_PROPERTIES
            if endpoint_property.name != "timeoutSeconds")),
    _DocumentSection(
        "nativeBrainAnthropic", "A native tool-calling brain on the Anthropic Messages API.",
        (_OBJECT,),
        '{ "apiKey": "k", "model": "claude-sonnet-5" }',
        properties=(
            _DocumentProperty("apiKey", _STRING, required=True),
            _DocumentProperty("model", _STRING, required=True),
            _DocumentProperty("temperature", _NUMBER),
            _DocumentProperty("maxTokens", _INTEGER, positive=True),
        )),
    _DocumentSection(
        "skills", "A skills folder, or several.", (_STRING, _ARRAY), '"Skills"',
        items_kind=_STRING),
    _DocumentSection(
        "knowledge", "A knowledge folder, or the folder with its pattern and ranking.",
        (_STRING, _OBJECT),
        '"Knowledge"',
        properties=(
            _DocumentProperty("path", _STRING, required=True),
            _DocumentProperty("pattern", _STRING),
            _DocumentProperty("maxResults", _INTEGER, positive=True),
            _DocumentProperty("minScore", _NUMBER),
        )),
    _DocumentSection(
        "memory", "A memory file, or false to run without one.", (_STRING, _BOOLEAN),
        '"memory.txt"',
        boolean_must_be_false=True),
    _DocumentSection(
        "mcp", "An MCP server by URL, or with its auth, or a command that starts one, or several.",
        (_STRING, _OBJECT, _ARRAY),
        '"http://localhost:8080/mcp/"',
        properties=(
            _DocumentProperty("endpointUrl", _STRING),
            _DocumentProperty("relativeUrl", _STRING),
            _DocumentProperty("timeoutSeconds", _INTEGER, positive=True),
            _DocumentProperty("bearerToken", _STRING),
            _DocumentProperty("apiKey", _STRING),
            _DocumentProperty("apiKeyHeader", _STRING),
            _DocumentProperty("command", _STRING),
            _DocumentProperty("arguments", _ARRAY),
            _DocumentProperty("args", _ARRAY),
            _DocumentProperty("environmentVariables", _OBJECT),
            _DocumentProperty("env", _OBJECT),
            _DocumentProperty("workingDirectory", _STRING),
        ),
        items_section="mcp"),
    _DocumentSection(
        "agents", "A folder of agent documents, or inline members, for handoffs.",
        (_STRING, _ARRAY),
        '"Agents"',
        items_section="agents"),
    _DocumentSection(
        "gate", "The guardian that screens the request, on an endpoint.", (_OBJECT,),
        _ENDPOINT_EXAMPLE,
        properties=_ENDPOINT_PROPERTIES),
    _DocumentSection(
        "ruleGate", "Patterns the gate refuses without a model.", (_ARRAY,), '["password"]',
        items_kind=_STRING),
    _DocumentSection(
        "judge", "The guardian that reviews the answer, on an endpoint.", (_OBJECT,),
        _ENDPOINT_EXAMPLE,
        properties=_ENDPOINT_PROPERTIES),
    _DocumentSection(
        "ruleJudge", "Patterns the judge rejects without a model.", (_ARRAY,), '["as an AI"]',
        items_kind=_STRING),
    _DocumentSection(
        "contract", "The JSON Schema the answer must satisfy, embedded.", (_OBJECT,),
        '{ "type": "object" }'),
    _DocumentSection(
        "constitution", "The law above both guardians, a Markdown file.", (_STRING,),
        '"Constitution/ethics.md"'),
    _DocumentSection(
        "consumption", "The consumption prompt, a Markdown file.", (_STRING,),
        '"Consumption/rules.md"'),
    _DocumentSection(
        "redact",
        "PII redaction at the brain boundary: true for the default rules, or your own.",
        (_BOOLEAN, _OBJECT),
        "true",
        properties=(_DocumentProperty("rules", _ARRAY, required=True),)),
    _DocumentSection("maxTurns", "How many turns a run may take.", (_INTEGER,), "7"),
    _DocumentSection(
        "identicalCallLimit",
        "How many times a run may ask for an act the ledger already answered.",
        (_INTEGER,),
        "8"),
    _DocumentSection(
        "citeKnowledge",
        "End each answer with the sources of its knowledge: true, false, or the line's prefix.",
        (_BOOLEAN, _STRING),
        "true"),
    _DocumentSection(
        "allowTools", "The only tools the agent may call; empty closes the perimeter.",
        (_ARRAY,),
        '["calculator"]',
        items_kind=_STRING),
    _DocumentSection(
        "permissions", "The disposition toward acts nothing names.", (_STRING,), '"Ask"',
        names=("Open", "Ask", "Deny")),
    _DocumentSection(
        "risk", "Which tools carry which risk level.", (_OBJECT,),
        '{ "Irreversible": ["wire_transfer"] }',
        properties=(
            _DocumentProperty("Safe", _ARRAY),
            _DocumentProperty("Sensitive", _ARRAY),
            _DocumentProperty("Irreversible", _ARRAY),
        )),
    _DocumentSection(
        "requireApproval", "Tools a person must approve before they run.", (_ARRAY,),
        '["wire_transfer"]',
        items_kind=_STRING),
    _DocumentSection(
        "logTo", "The human-readable trace, a file, or the file with its verbosity.",
        (_STRING, _OBJECT),
        '"log.txt"',
        properties=(
            _DocumentProperty("path", _STRING, required=True),
            _DocumentProperty("verbosity", _STRING, names=("Summary", "Natures", "Full")),
        )),
    _DocumentSection("audit", "The decision log, JSON lines.", (_STRING,), '"audit.jsonl"'),
    _DocumentSection(
        "auditPayloads", "Record payloads in the decision log, as redaction leaves them.",
        (_BOOLEAN,),
        "true"),
    _DocumentSection(
        "telemetry", "OpenTelemetry spans and metrics, under this service name, or true.",
        (_STRING, _BOOLEAN),
        '"teller-agent"'),
    _DocumentSection(
        "sessions", "Conversations kept in a folder, or the folder with its history bound.",
        (_STRING, _OBJECT),
        '"Sessions"',
        properties=(
            _DocumentProperty("path", _STRING, required=True),
            _DocumentProperty("maxHistoryTurns", _INTEGER, positive=True),
        )),
    _DocumentSection("effectLedger", "The run-once ledger folder.", (_STRING,), '"ledger"'),
    _DocumentSection(
        "effectLeaseSeconds", "How long an in-flight claim is presumed live.", (_NUMBER,),
        "300"),
    _DocumentSection(
        "screenToolOutput", "Screen tool results with the gate before the brain sees them.",
        (_BOOLEAN,),
        "true"),
    _DocumentSection(
        "budget", "Bounds on tokens, cost and wall clock.", (_OBJECT,),
        '{ "maxTokens": 50000 }',
        properties=(
            _DocumentProperty("maxTokens", _INTEGER, positive=True),
            _DocumentProperty("maxCostUsd", _NUMBER, positive=True),
            _DocumentProperty("maxWallClockSeconds", _NUMBER, positive=True),
            _DocumentProperty("costPerThousandTokens", _NUMBER),
        )),
    _DocumentSection(
        "usage", "How tokens are counted when the provider does not say.", (_OBJECT,),
        '{ "charactersPerToken": 4 }',
        properties=(_DocumentProperty("charactersPerToken", _NUMBER, positive=True),)),
    _DocumentSection(
        "resilience", "Retries on the brain, as a count or an object.", (_INTEGER, _OBJECT),
        "3",
        properties=(_DocumentProperty("retries", _INTEGER),)),
    _DocumentSection(
        "compensateOnFailure", "Unwind performed effects when the run fails.", (_BOOLEAN,),
        "true"),
)

# Nested object sections, validated by the same table under a dotted key.
_NESTED_SECTIONS = (
    _DocumentSection(
        "redact.rules", "One redaction rule: a label and a pattern.", (_OBJECT,),
        r'{ "label": "CARD", "pattern": "\\d{4}-\\d{4}-\\d{4}-\\d{4}" }',
        properties=(
            _DocumentProperty("label", _STRING, required=True),
            _DocumentProperty("pattern", _STRING, required=True),
        )),
)


def document_property_names(key: str) -> tuple[str, ...]:
    """The properties an object section accepts, from the one table the schema is emitted from."""
    (section,) = [
        section for section in (*_DOCUMENT_SECTIONS, *_NESTED_SECTIONS) if section.key == key]

    return tuple(document_property.name for document_property in section.properties)
