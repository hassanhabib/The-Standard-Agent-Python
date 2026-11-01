# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Callable, Mapping

from standard_agents.brokers.telemetries.telemetry_broker import Disposable, TelemetryBroker

_EMPTY_ATTRIBUTES: Mapping[str, Any] = MappingProxyType({})


# The Custom mode of the telemetry seam: every boundary the loop crosses arrives at one function
# as a named event with its attributes, for a pipeline no listener reaches: StatsD, a log
# shipper, a metrics API of your own.
class FunctionTelemetryBroker(TelemetryBroker):
    def __init__(self, record: Callable[[str, Mapping[str, Any]], None]) -> None:
        self._record = record

    def start_run(self, session_id: str) -> Disposable | None:
        self._record("run.start", {"session.id": session_id})

        return _Scope(lambda: self._record("run.end", _EMPTY_ATTRIBUTES))

    def start_turn(self, turn: int) -> Disposable | None:
        self._record("turn.start", {"turn.index": turn})

        return _Scope(lambda: self._record("turn.end", _EMPTY_ATTRIBUTES))

    def record_turn_usage(self, prompt_tokens: int, completion_tokens: int, estimated: bool) -> None:
        self._record(
            "turn.usage",
            {
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "estimated": estimated,
            })

    def record_run_outcome(self, status: str, prompt_tokens: int, completion_tokens: int) -> None:
        self._record(
            "run.outcome",
            {
                "status": status,
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
            })


# Every dispose() ends the scope again, as every Dispose() does in C#.
class _Scope:
    def __init__(self, end: Callable[[], None]) -> None:
        self._end = end

    def dispose(self) -> None:
        self._end()

    def __enter__(self) -> _Scope:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.dispose()
