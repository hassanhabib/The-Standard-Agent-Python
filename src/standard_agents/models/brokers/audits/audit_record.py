# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from standard_agents.models.brokers.audits.audit_kind import AuditKind

# default(DateTimeOffset): 0001-01-01T00:00:00+00:00.
_DATE_TIME_OFFSET_MIN = datetime(1, 1, 1, tzinfo=timezone.utc)

_DATE_TIME_OFFSET_PATTERN = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})"
    r"(?:T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,16}))?)?"
    r"(Z|[+-]\d{2}(?::\d{2})?)?)?$")


@dataclass(frozen=True)
class AuditRecord:
    run_id: str = ""
    sequence: int = 0
    timestamp: datetime = _DATE_TIME_OFFSET_MIN
    kind: AuditKind = AuditKind.RUN

    actor: str = ""
    message: str = ""
    detail: bool = False

    principal: str | None = None

    # The payload behind a process record (the prompt, the system prompt, the reply, a tool's
    # input or output), present only when the deployment opted into payload capture and then
    # as the redaction left it. Withheld by default: the decision log records that a payload
    # existed, how large it was and which one it was (payload_length, payload_hash), never the
    # payload itself (principal review 2026-09-04, F-14).
    payload: str | None = None
    payload_length: int | None = None
    payload_hash: str | None = None
    previous_hash: str | None = None

    # The FileAuditBroker wire: camelCase names, null values omitted (WhenWritingNull), enums
    # as camelCase strings, properties in declaration order.
    def to_json_dict(self) -> dict:
        values = {
            "runId": self.run_id,
            "sequence": self.sequence,
            "timestamp": _format_date_time_offset(self.timestamp),
            "kind": _enum_to_json(self.kind),
            "actor": self.actor,
            "message": self.message,
            "detail": self.detail,
            "principal": self.principal,
            "payload": self.payload,
            "payloadLength": self.payload_length,
            "payloadHash": self.payload_hash,
            "previousHash": self.previous_hash,
        }

        return {key: value for key, value in values.items() if value is not None}

    # Case-sensitive camelCase names; an absent property keeps its default.
    @classmethod
    def from_json_dict(cls, data: dict) -> AuditRecord:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to AuditRecord.")

        arguments: dict[str, Any] = {}

        if "runId" in data:
            arguments["run_id"] = _as_string(data["runId"])

        if "sequence" in data:
            arguments["sequence"] = _as_int32(data["sequence"])

        if "timestamp" in data:
            arguments["timestamp"] = _parse_date_time_offset(data["timestamp"])

        if "kind" in data:
            arguments["kind"] = _enum_from_json(AuditKind, data["kind"])

        if "actor" in data:
            arguments["actor"] = _as_string(data["actor"])

        if "message" in data:
            arguments["message"] = _as_string(data["message"])

        if "detail" in data:
            arguments["detail"] = _as_bool(data["detail"])

        if "principal" in data:
            arguments["principal"] = _as_string(data["principal"])

        if "payload" in data:
            arguments["payload"] = _as_string(data["payload"])

        if "payloadLength" in data:
            value = data["payloadLength"]
            arguments["payload_length"] = None if value is None else _as_int32(value)

        if "payloadHash" in data:
            arguments["payload_hash"] = _as_string(data["payloadHash"])

        if "previousHash" in data:
            arguments["previous_hash"] = _as_string(data["previousHash"])

        return cls(**arguments)


def _as_string(value: Any) -> str | None:
    if value is None or isinstance(value, str):
        return value

    raise ValueError("The JSON value could not be converted to System.String.")


def _as_int32(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and -2**31 <= value < 2**31:
        return value

    raise ValueError("The JSON value could not be converted to System.Int32.")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    raise ValueError("The JSON value could not be converted to System.Boolean.")


# JsonStringEnumConverter(JsonNamingPolicy.CamelCase): Run -> "run".
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


# System.Text.Json writes a DateTimeOffset as yyyy-MM-ddTHH:mm:ss.FFFFFFFzzz: the fraction
# trimmed of trailing zeros and dropped when zero, the offset always as +HH:mm.
def _format_date_time_offset(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.astimezone()

    offset_seconds = int(value.utcoffset().total_seconds())
    sign = "-" if offset_seconds < 0 else "+"
    offset_minutes = abs(offset_seconds) // 60

    text = (
        f"{value.year:04d}-{value.month:02d}-{value.day:02d}"
        f"T{value.hour:02d}:{value.minute:02d}:{value.second:02d}")

    if value.microsecond:
        text += "." + f"{value.microsecond:06d}".rstrip("0")

    return text + f"{sign}{offset_minutes // 60:02d}:{offset_minutes % 60:02d}"


# ISO 8601 as System.Text.Json reads a DateTimeOffset; no offset means the local one.
def _parse_date_time_offset(value: Any) -> datetime:
    match = _DATE_TIME_OFFSET_PATTERN.match(value) if isinstance(value, str) else None

    if match is None:
        raise ValueError("The JSON value could not be converted to System.DateTimeOffset.")

    year, month, day, hour, minute, second, fraction, offset = match.groups()
    microsecond = int((fraction or "")[:6].ljust(6, "0"))

    moment = datetime(
        int(year), int(month), int(day),
        int(hour or 0), int(minute or 0), int(second or 0),
        microsecond)

    if offset is None:
        return moment.astimezone()

    if offset == "Z":
        return moment.replace(tzinfo=timezone.utc)

    sign = -1 if offset[0] == "-" else 1
    hours = int(offset[1:3])
    minutes = int(offset[4:6]) if len(offset) > 3 else 0

    return moment.replace(
        tzinfo=timezone(sign * timedelta(hours=hours, minutes=minutes)))
