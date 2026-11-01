# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol


# C#'s Disposable: a scope closed by dispose(). Every scope this seam hands out is also a
# context manager.
class Disposable(Protocol):
    def dispose(self) -> None:
        ...


# The telemetry seam: spans and metrics for the run the way LoggingBroker is prose and
# AuditBroker is records. A utility broker: held by the loop, exempt from the dependency count,
# and structurally unable to change what the agent decides or does.
class TelemetryBroker(ABC):
    # Opens the run scope. Dispose it to close the scope; a None return means nothing is
    # listening and there is no scope to close.
    @abstractmethod
    def start_run(self, session_id: str) -> Disposable | None:
        ...

    # Opens one turn's scope inside the run scope.
    @abstractmethod
    def start_turn(self, turn: int) -> Disposable | None:
        ...

    # Records what one turn's model calls consumed, and whether it was counted or reported.
    @abstractmethod
    def record_turn_usage(self, prompt_tokens: int, completion_tokens: int, estimated: bool) -> None:
        ...

    # Records how the run ended and what it consumed in total.
    @abstractmethod
    def record_run_outcome(self, status: str, prompt_tokens: int, completion_tokens: int) -> None:
        ...
