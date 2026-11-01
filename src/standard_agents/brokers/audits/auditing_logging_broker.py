# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import hashlib
from typing import Callable

from standard_agents.brokers.audits.iaudit_broker import IAuditBroker
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.redactions.iredaction_broker import IRedactionBroker
from standard_agents.brokers.times.itime_broker import ITimeBroker
from standard_agents.models.brokers.audits.audit_kind import AuditKind
from standard_agents.models.brokers.audits.audit_policy import AuditPolicy
from standard_agents.models.brokers.audits.audit_record import AuditRecord
from standard_agents.models.loggings.agent_run import AgentRun
from standard_agents.models.loggings.agent_step import AgentStep


# The decision log, applied by decoration: every event the loop narrates to its log is also
# written to the audit sink as a durable record, stamped, sequenced and attributed, and the
# logging broker underneath never learns the audit exists. A decorator implements the very
# interface it takes, so it adds one concern to the call it wraps and owns no resource of its
# own; that is the one shape in which a broker may hold another (principal review 2026-09-04,
# F-16). Composed at the facade only when an audit sink is configured, over whichever logging
# broker the deployment chose.
#
# What the record carries is policy (F-14): metadata by default (a payload's length and hash,
# never the payload) and the payload itself only when the deployment opted in, as the configured
# redaction leaves it. Redact protects the model boundary; this is the same rule at the audit
# boundary.
class AuditingLoggingBroker(ILoggingBroker):
    def __init__(
            self,
            logging_broker: ILoggingBroker,
            audit_broker: IAuditBroker,
            time_broker: ITimeBroker,
            redaction_broker: IRedactionBroker,
            policy: AuditPolicy,
            principal: Callable[[], str | None] | None = None) -> None:

        self._logging_broker = logging_broker
        self._audit_broker = audit_broker
        self._time_broker = time_broker
        self._redaction_broker = redaction_broker
        self._policy = policy
        self._principal = principal

        # The run is read from the ambient AgentRun that Coordination begins (SPEC.md 4.4); the
        # fallback covers a broker driven outside the loop.
        self._fallback_run = AgentRun.detached()

    @property
    def _run(self) -> AgentRun:
        current = AgentRun.current()

        return current if current is not None else self._fallback_run

    async def log_information(self, message: str) -> None:
        await self._logging_broker.log_information(message)

    async def log_trace(self, message: str) -> None:
        await self._logging_broker.log_trace(message)

    async def log_debug(self, message: str) -> None:
        await self._logging_broker.log_debug(message)

    async def log_warning(self, message: str) -> None:
        await self._logging_broker.log_warning(message)

    async def log_error(self, exception: BaseException) -> None:
        await self._audit(AuditKind.ERROR, actor="Agent", message=str(exception))
        await self._logging_broker.log_error(exception)

    async def log_critical(self, exception: BaseException) -> None:
        await self._audit(AuditKind.ERROR, actor="Agent", message=str(exception))
        await self._logging_broker.log_critical(exception)

    # The trace underneath resets; the decision log is durable and records the start instead
    # (SPEC.md 4.7).
    async def log_reset(self) -> None:
        await self._audit(AuditKind.RUN, actor="Agent", message="run started")
        await self._logging_broker.log_reset()

    async def log_turn(self, turn: int) -> None:
        await self._audit(AuditKind.TURN, actor="Agent", message=f"turn {turn}")
        await self._logging_broker.log_turn(turn)

    async def log_outcome(self, message: str) -> None:
        await self._audit(AuditKind.OUTCOME, actor="Agent", message=message)
        await self._logging_broker.log_outcome(message)

    async def log_step(self, step: AgentStep) -> None:
        await self._audit(AuditKind.STEP, actor=_step_name(step), message=_step_name(step))
        await self._logging_broker.log_step(step)

    async def log_process(self, actor: str, message: str, detail: bool = False) -> None:
        await self._audit(AuditKind.PROCESS, actor, message, detail)
        await self._logging_broker.log_process(actor, message, detail)

    # The summary is the record; the payload is its length and its hash, and the payload itself
    # only under a policy that asked for it, redacted, because the sink outlives the run.
    async def log_payload(self, actor: str, summary: str, payload: str, detail: bool) -> None:
        recorded = (
            self._redaction_broker.redact(payload, {})
            if self._policy.payloads
            else None)

        await self._audit(
            AuditKind.PROCESS,
            actor,
            summary,
            detail,
            recorded,
            _utf16_length(payload),
            _hash(payload))

        await self._logging_broker.log_payload(actor, summary, payload, detail)

    async def _audit(
            self,
            kind: AuditKind,
            actor: str,
            message: str,
            detail: bool = False,
            payload: str | None = None,
            payload_length: int | None = None,
            payload_hash: str | None = None) -> None:

        run = self._run

        record = AuditRecord(
            run_id=run.id,
            sequence=run.next_sequence(),
            timestamp=self._time_broker.get_current_date_time_offset(),
            kind=kind,
            actor=actor,
            message=message,
            detail=detail,
            principal=self._principal() if self._principal is not None else None,
            payload=payload,
            payload_length=payload_length,
            payload_hash=payload_hash)

        await self._audit_broker.write(record)


# Enum.ToString(): the member's C# name, AgentStep.DATA as "Data".
def _step_name(step: AgentStep) -> str:
    return "".join(word.capitalize() for word in step.name.split("_"))


# string.Length: UTF-16 code units, so a character outside the Basic Multilingual Plane counts
# as two.
def _utf16_length(text: str) -> int:
    return len(text.encode("utf-16-le", errors="surrogatepass")) // 2


# The same fingerprint on both implementations: lowercase hex either way, so a hash written by
# one matches the same payload's hash written by the other.
def _hash(payload: str) -> str:
    return hashlib.sha256(_utf8_bytes(payload)).hexdigest()


# Encoding.UTF8.GetBytes: a lone surrogate encodes as U+FFFD, where Python's encoder would raise.
def _utf8_bytes(value: str) -> bytes:
    utf16 = value.encode("utf-16-le", errors="surrogatepass")

    return utf16.decode("utf-16-le", errors="replace").encode("utf-8")
