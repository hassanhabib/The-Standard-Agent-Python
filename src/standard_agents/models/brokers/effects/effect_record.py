# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from standard_agents.models.brokers.effects.effect_state import EffectState

# default(DateTimeOffset): 0001-01-01T00:00:00+00:00.
_DATE_TIME_OFFSET_MIN = datetime(1, 1, 1, tzinfo=timezone.utc)

_DATE_TIME_OFFSET_PATTERN = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})"
    r"(?:T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,16}))?)?"
    r"(Z|[+-]\d{2}(?::\d{2})?)?)?$")


# One act's line in the ledger: which act, who claimed it, when, for how long, where it stands,
# and what it produced. Written before the act and updated after it, so an act that executed
# and was never recorded is distinguishable from one that never ran (SPEC.md 4.9).
@dataclass(frozen=True)
class EffectRecord:
    idempotency_key: str = ""
    tool_name: str = ""
    state: EffectState = EffectState.IN_FLIGHT

    # The run that claimed the act, so a repeat can tell its own attempt from another run's.
    owner: str = ""
    claimed_on: datetime = _DATE_TIME_OFFSET_MIN

    # Until when an in-flight claim may be presumed live. Past it, a claim with no outcome is
    # an earlier attempt whose fate is unknown, and the ledger holds a repeat for reconciliation
    # rather than presuming either that it happened or that it did not.
    lease_until: datetime = _DATE_TIME_OFFSET_MIN
    outcome: str | None = None
    detail: str | None = None
    recorded_on: datetime | None = None

    # The FileEffectLedgerBroker wire: camelCase names, null values omitted (WhenWritingNull),
    # enums as camelCase strings, properties in declaration order.
    def to_json_dict(self) -> dict:
        values = {
            "idempotencyKey": self.idempotency_key,
            "toolName": self.tool_name,
            "state": _enum_to_json(self.state),
            "owner": self.owner,
            "claimedOn": _format_date_time_offset(self.claimed_on),
            "leaseUntil": _format_date_time_offset(self.lease_until),
            "outcome": self.outcome,
            "detail": self.detail,
            "recordedOn": (
                None if self.recorded_on is None
                else _format_date_time_offset(self.recorded_on)),
        }

        return {key: value for key, value in values.items() if value is not None}

    # Case-sensitive camelCase names; an absent property keeps its default.
    @classmethod
    def from_json_dict(cls, data: dict) -> EffectRecord:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to EffectRecord.")

        arguments: dict[str, Any] = {}

        if "idempotencyKey" in data:
            arguments["idempotency_key"] = _as_string(data["idempotencyKey"])

        if "toolName" in data:
            arguments["tool_name"] = _as_string(data["toolName"])

        if "state" in data:
            arguments["state"] = _enum_from_json(EffectState, data["state"])

        if "owner" in data:
            arguments["owner"] = _as_string(data["owner"])

        if "claimedOn" in data:
            arguments["claimed_on"] = _parse_date_time_offset(data["claimedOn"])

        if "leaseUntil" in data:
            arguments["lease_until"] = _parse_date_time_offset(data["leaseUntil"])

        if "outcome" in data:
            arguments["outcome"] = _as_string(data["outcome"])

        if "detail" in data:
            arguments["detail"] = _as_string(data["detail"])

        if "recordedOn" in data:
            value = data["recordedOn"]
            arguments["recorded_on"] = None if value is None else _parse_date_time_offset(value)

        return cls(**arguments)


def _as_string(value: Any) -> str | None:
    if value is None or isinstance(value, str):
        return value

    raise ValueError("The JSON value could not be converted to System.String.")


# JsonStringEnumConverter(JsonNamingPolicy.CamelCase): InFlight -> "inFlight".
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
