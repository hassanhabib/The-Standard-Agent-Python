# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel


# One exchange: what was asked, what came back, and the work that produced it.
@dataclass(frozen=True)
class AgentTurn:
    prompt: str
    answer: str

    # The native calls this turn made and what they returned, oldest first.
    #
    # A turn is not only what was said. It is what the agent did in order to be able to say it,
    # and a history that keeps the answer while dropping the call that produced it tells the next
    # prompt that the agent answered but never how. A caller that holds the conversation itself
    # then has nowhere to put a finished call except the current turn's exchange list, where it
    # reads as this turn's evidence rather than as something already done (SPEC.md 4.11,
    # SPEC.md 6). Empty for a turn that called nothing, which is every turn the text protocol
    # produces.
    exchanges: tuple[ToolExchange, ...] = ()

    def to_json_dict(self) -> dict:
        values = {
            "prompt": self.prompt,
            "answer": self.answer,
            "exchanges": _list_to_json(self.exchanges, _tool_exchange_to_json),
        }

        return _without_nulls(values)

    @classmethod
    def from_json_dict(cls, data: dict) -> AgentTurn:
        _require_object(data, "AgentTurn")

        # Constructor parameters absent from the JSON are default(string), which is null.
        arguments: dict[str, Any] = {
            "prompt": _as_string(data.get("prompt")),
            "answer": _as_string(data.get("answer")),
        }

        if "exchanges" in data:
            arguments["exchanges"] = _list_from_json(
                data["exchanges"], _tool_exchange_from_json, "ToolExchange")

        return cls(**arguments)


# One conversation: what was said, and what it was left in the middle of.
#
# Invariant 4 says the agent instance is stateless across prompts. It does not say the
# conversation is (SPEC.md 4.11). The session is where continuity lives (outside the agent, in a
# broker), which is what lets a pause be resumed by a different process, or by a different
# machine, long after the instance that created it is gone.
@dataclass(frozen=True)
class AgentSession:
    id: str = ""

    # What was said before, oldest first.
    history: tuple[AgentTurn, ...] = ()

    # What the session was left in the middle of, if anything.
    status: AgentStatus = AgentStatus.WORKING

    # The question the agent asked and is waiting on, when awaiting input.
    pending_question: str = ""

    # The act this session is waiting on an authority to permit, when awaiting approval
    # (SPEC.md 4.11, 4.9).
    #
    # The act travels with the session, not just the fact that something is waiting. A process
    # that picks the session up has to be able to show a human what they are approving, and an
    # approval broker has to be able to check that the act it is now being asked about is the
    # act that was held: its idempotency_key is what makes that checkable.
    pending_effect: AgentEffect | None = None

    # The run that last worked this session, written when the run starts.
    #
    # Written at the start rather than at the end because a crash means nothing at the end runs
    # at all. It is what lets a resumed run keep the identity the interrupted one had, and
    # therefore derive the same idempotency keys (SPEC.md 4.9), so an effect that already went
    # out is replayed rather than performed a second time.
    run_id: str = ""

    # The principal that opened this session, stamped on the first write and kept. A session
    # id is caller-provided, so without an owner two callers sharing or guessing one id share
    # one history; with one, a different principal is refused. Empty when no principal was
    # configured, which is the anonymous, shared-by-id behavior that existed before.
    owner: str = ""

    # The version this record was written as, one more than the version it was read at. A
    # store that honors it refuses a write based on a stale read, so two prompts in one session
    # at once cannot erase each other's completed turn; the loop re-reads and tries again.
    # Zero for a record written before versions existed.
    version: int = 0

    # The FileSessionBroker wire: camelCase names, null values omitted (WhenWritingNull), enums
    # as camelCase strings, properties in declaration order, nested records included.
    def to_json_dict(self) -> dict:
        values = {
            "id": self.id,
            "history": _list_to_json(self.history, lambda turn: turn.to_json_dict()),
            "status": _enum_to_json(self.status),
            "pendingQuestion": self.pending_question,
            "pendingEffect": (
                None if self.pending_effect is None
                else _agent_effect_to_json(self.pending_effect)),
            "runId": self.run_id,
            "owner": self.owner,
            "version": self.version,
        }

        return _without_nulls(values)

    # Case-sensitive camelCase names; an absent property keeps its default.
    @classmethod
    def from_json_dict(cls, data: dict) -> AgentSession:
        _require_object(data, "AgentSession")
        arguments: dict[str, Any] = {}

        if "id" in data:
            arguments["id"] = _as_string(data["id"])

        if "history" in data:
            arguments["history"] = _list_from_json(
                data["history"], AgentTurn.from_json_dict, "AgentTurn")

        if "status" in data:
            arguments["status"] = _enum_from_json(AgentStatus, data["status"])

        if "pendingQuestion" in data:
            arguments["pending_question"] = _as_string(data["pendingQuestion"])

        if "pendingEffect" in data:
            value = data["pendingEffect"]
            arguments["pending_effect"] = None if value is None else _agent_effect_from_json(value)

        if "runId" in data:
            arguments["run_id"] = _as_string(data["runId"])

        if "owner" in data:
            arguments["owner"] = _as_string(data["owner"])

        if "version" in data:
            arguments["version"] = _as_int64(data["version"])

        return cls(**arguments)


# The nested records the session carries, written under the same serializer options.
def _tool_exchange_to_json(exchange: ToolExchange) -> dict:
    return _without_nulls({
        "callId": exchange.call_id,
        "toolName": exchange.tool_name,
        "argumentsJson": exchange.arguments_json,
        "result": exchange.result,
        "replayed": exchange.replayed,
    })


def _tool_exchange_from_json(data: Any) -> ToolExchange:
    _require_object(data, "ToolExchange")

    arguments: dict[str, Any] = {
        "call_id": _as_string(data.get("callId")),
        "tool_name": _as_string(data.get("toolName")),
        "arguments_json": _as_string(data.get("argumentsJson")),
        "result": _as_string(data.get("result")),
    }

    if "replayed" in data:
        arguments["replayed"] = _as_bool(data["replayed"])

    return ToolExchange(**arguments)


def _agent_principal_to_json(principal: AgentPrincipal) -> dict:
    return _without_nulls({
        "id": principal.id,
        "tenantId": principal.tenant_id,
        "jurisdiction": principal.jurisdiction,
        "delegatedBy": principal.delegated_by,
    })


def _agent_principal_from_json(data: Any) -> AgentPrincipal:
    _require_object(data, "AgentPrincipal")
    arguments: dict[str, Any] = {}

    for json_name, field_name in (
            ("id", "id"),
            ("tenantId", "tenant_id"),
            ("jurisdiction", "jurisdiction"),
            ("delegatedBy", "delegated_by")):
        if json_name in data:
            arguments[field_name] = _as_string(data[json_name])

    return AgentPrincipal(**arguments)


def _agent_effect_to_json(effect: AgentEffect) -> dict:
    return _without_nulls({
        "runId": effect.run_id,
        "principal": effect.principal,
        "identity": (
            None if effect.identity is None
            else _agent_principal_to_json(effect.identity)),
        "toolName": effect.tool_name,
        "arguments": effect.arguments,
        "callId": effect.call_id,
        "scope": effect.scope,
        "riskLevel": _enum_to_json(effect.risk_level),
        "approvalRequired": effect.approval_required,
        "idempotencyKey": effect.idempotency_key,
    })


# Read property by property, as the serializer does: the idempotency key is taken as stored,
# never re-derived.
def _agent_effect_from_json(data: Any) -> AgentEffect:
    _require_object(data, "AgentEffect")
    arguments: dict[str, Any] = {}

    for json_name, field_name in (
            ("runId", "run_id"),
            ("principal", "principal"),
            ("toolName", "tool_name"),
            ("arguments", "arguments"),
            ("callId", "call_id"),
            ("scope", "scope"),
            ("idempotencyKey", "idempotency_key")):
        if json_name in data:
            arguments[field_name] = _as_string(data[json_name])

    if "identity" in data:
        value = data["identity"]
        arguments["identity"] = None if value is None else _agent_principal_from_json(value)

    if "riskLevel" in data:
        arguments["risk_level"] = _enum_from_json(RiskLevel, data["riskLevel"])

    if "approvalRequired" in data:
        arguments["approval_required"] = _as_bool(data["approvalRequired"])

    return AgentEffect(**arguments)


def _without_nulls(values: dict) -> dict:
    return {key: value for key, value in values.items() if value is not None}


def _list_to_json(items: Any, write: Any) -> list | None:
    if items is None:
        return None

    return [None if item is None else write(item) for item in items]


def _list_from_json(value: Any, read: Any, type_name: str) -> tuple | None:
    if value is None:
        return None

    if not isinstance(value, list):
        raise ValueError(f"The JSON value could not be converted to IReadOnlyList<{type_name}>.")

    return tuple(None if item is None else read(item) for item in value)


def _require_object(data: Any, type_name: str) -> None:
    if not isinstance(data, dict):
        raise ValueError(f"The JSON value could not be converted to {type_name}.")


def _as_string(value: Any) -> str | None:
    if value is None or isinstance(value, str):
        return value

    raise ValueError("The JSON value could not be converted to System.String.")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    raise ValueError("The JSON value could not be converted to System.Boolean.")


def _as_int64(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and -2**63 <= value < 2**63:
        return value

    raise ValueError("The JSON value could not be converted to System.Int64.")


# JsonStringEnumConverter(JsonNamingPolicy.CamelCase): AwaitingInput -> "awaitingInput".
def _enum_to_json(value: Any) -> str:
    words = value.name.split("_")

    return words[0].lower() + "".join(word.capitalize() for word in words[1:])


# Reads the enum's name ignoring case, or its integer value.
def _enum_from_json(enum_type: Any, value: Any) -> Any:
    if isinstance(value, int) and not isinstance(value, bool):
        return enum_type(value)

    if isinstance(value, str):
        text = value.strip()

        for member in enum_type:
            if member.name.replace("_", "").lower() == text.lower():
                return member

        if re.fullmatch(r"[+-]?\d+", text):
            return enum_type(int(text))

    raise ValueError(f"The JSON value could not be converted to {enum_type.__name__}.")
