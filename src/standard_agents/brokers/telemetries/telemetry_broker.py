# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Protocol


class TelemetryScope(Protocol):
    """A scope the caller closes: call close(), or use it in a with block.

    Every scope this seam hands out supports both.
    """

    def close(self) -> None:
        ...

    def __enter__(self) -> TelemetryScope:
        ...

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None) -> None:
        ...


class TelemetryBroker(ABC):
    """The telemetry seam: spans and metrics for the run.

    Spans and metrics the way LoggingBroker is prose and AuditBroker is records. A utility
    broker: held by the loop, exempt from the dependency count, and structurally unable to
    change what the agent decides or does.
    """

    @abstractmethod
    def start_run(self, session_id: str) -> TelemetryScope | None:
        """Open the run scope.

        Close it to end the scope; a None return means nothing is listening and there is no
        scope to close.
        """

    @abstractmethod
    def start_turn(self, turn: int) -> TelemetryScope | None:
        """Open one turn's scope inside the run scope."""

    @abstractmethod
    def record_turn_usage(
            self,
            prompt_tokens: int,
            completion_tokens: int,
            estimated: bool) -> None:
        """Record what one turn's model calls consumed, and whether it was counted or reported."""

    @abstractmethod
    def record_run_outcome(self, status: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Record how the run ended and what it consumed in total."""
