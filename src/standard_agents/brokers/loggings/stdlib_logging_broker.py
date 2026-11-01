# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import logging
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.loggings.agent_run import AgentRun
from standard_agents.models.loggings.agent_step import AgentStep
from standard_agents.models.loggings.trace_verbosity import TraceVerbosity

# Microsoft.Extensions.Logging's Trace sits below Debug; Python's logging has no such level.
_TRACE = 5

# string.ReplaceLineEndings: CRLF, CR, LF, NEL, LS, FF and PS are each one line ending.
_LINE_ENDING = re.compile("\r\n|[\r\n\f\u0085  ]")


class StdlibLoggingBroker(LoggingBroker):
    """One resource, wrapped: the log.

    Both of its faces are the same sink: the logger the host gave us, and the human-readable
    trace file that is that log written to disk. Nothing else lives here. The decision log is
    another resource with another broker, and the two meet only by decoration at composition
    (AuditingLoggingBroker), never by this broker holding that one (principal review 2026-09-04,
    F-16).
    """

    def __init__(
            self,
            logger: logging.Logger,
            verbosity: TraceVerbosity = TraceVerbosity.FULL,
            log_path: str | None = None) -> None:

        self._logger = logger
        self._verbosity = verbosity
        self._log_path = None if log_path is None else os.path.abspath(log_path)

        # No run state lives here. SPEC.md 4.4: run identity and counters are per invocation,
        # never per instance; one broker serves every concurrent run, so a field here would let
        # one prompt overwrite another's record. The run is read from the ambient AgentRun that
        # Coordination begins; the fallback run covers a broker driven outside the loop.
        self._fallback_run = AgentRun.detached()
        self._trace_lock = threading.Lock()

    @property
    def _run(self) -> AgentRun:
        current = AgentRun.current()

        return current if current is not None else self._fallback_run

    async def log_information(self, message: str) -> None:
        self._logger.info(message)

    async def log_trace(self, message: str) -> None:
        self._logger.log(_TRACE, message)

    async def log_debug(self, message: str) -> None:
        self._logger.debug(message)

    async def log_warning(self, message: str) -> None:
        self._logger.warning(message)

    async def log_error(self, exception: BaseException) -> None:
        self._logger.error(str(exception), exc_info=exception)
        await self._emit(f"  → ERROR: {_replace_line_endings(str(exception), ' ')}")

    async def log_critical(self, exception: BaseException) -> None:
        self._logger.critical(str(exception), exc_info=exception)
        await self._emit(f"  → CRITICAL: {_replace_line_endings(str(exception), ' ')}")

    async def log_reset(self) -> None:
        """Starts a run.

        The human-readable trace is transient and is reset here; the decision log is durable
        and is not touched by this broker at all (SPEC.md 4.7).
        """
        self._run.reset_process_index()
        self._run.started_on = datetime.now(timezone.utc)

        if self._log_path is not None:
            with self._trace_lock:
                with open(self._log_path, "w", encoding="utf-8", newline="") as file:
                    file.write("")

    async def log_turn(self, turn: int) -> None:
        await self._emit(f"{os.linesep}Turn {turn}")

    async def log_outcome(self, message: str) -> None:
        elapsed = datetime.now(timezone.utc) - self._run.started_on
        await self._emit(f"  → {message} ({_total_milliseconds_f0(elapsed)}ms)")

    async def log_step(self, step: AgentStep) -> None:
        self._run.reset_process_index()

        if TraceVerbosity.NATURES.value <= self._verbosity.value:
            await self._emit(f"  Step {step.value}: {_step_name(step)}")

    async def log_process(self, actor: str, message: str, detail: bool = False) -> None:
        level = TraceVerbosity.FULL if detail else TraceVerbosity.NATURES

        if level.value <= self._verbosity.value:
            indented = _replace_line_endings(message, f"{os.linesep}      ")
            await self._emit(f"    Process {self._run.next_process_index()}: {actor}: {indented}")

    async def log_payload(self, actor: str, summary: str, payload: str, detail: bool) -> None:
        """Writes the payload in full, because the trace is the human's reading aid.

        On the same line as the summary when it fits, under the summary when it spans lines.
        """
        separator = os.linesep if "\n" in payload else " "

        await self.log_process(actor, f"{summary} →{separator}{payload}", detail)

    async def _emit(self, line: str) -> None:
        """Writes one line to the trace file, or to the logger when there is no file.

        The trace is a shared file and one broker serves every concurrent run, so writes are
        serialized: without this, sixty-four prompts in flight collide on the handle and most of
        them fail with an OSError rather than an answer.

        Concurrent runs interleave in the trace, and each run's reset truncates it. That is the
        trace being what SPEC.md 4.7 calls it: transient, a development aid, resettable. The
        artifact for a concurrent deployment is the decision log, which is append-only and keeps
        every run whole.
        """
        if self._log_path is None:
            self._logger.info(line)

            return

        with self._trace_lock:
            with open(self._log_path, "a", encoding="utf-8", newline="") as file:
                file.write(line + os.linesep)


def _replace_line_endings(text: str, replacement: str) -> str:
    return _LINE_ENDING.sub(lambda match: replacement, text)


def _step_name(step: AgentStep) -> str:
    """The step as .NET's Enum.ToString() names it: AgentStep.DATA as "Data"."""
    return "".join(word.capitalize() for word in step.name.split("_"))


def _total_milliseconds_f0(elapsed: timedelta) -> str:
    """TimeSpan.TotalMilliseconds formatted F0: whole milliseconds.

    A midpoint rounds away from zero, as .NET rounds it (Python's own formatting rounds a
    midpoint to even).
    """
    microseconds = elapsed // timedelta(microseconds=1)
    milliseconds = Decimal(microseconds) / Decimal(1000)

    return str(milliseconds.quantize(Decimal(1), rounding=ROUND_HALF_UP))
