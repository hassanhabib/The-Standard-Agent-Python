# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.telemetries.itelemetry_broker import IDisposable, ITelemetryBroker


# The default when no telemetry was asked for: every scope is nothing and every record goes
# nowhere, so an agent that never called .telemetry() spends nothing on it.
class NotConfiguredTelemetryBroker(ITelemetryBroker):
    def start_run(self, session_id: str) -> IDisposable | None:
        return None

    def start_turn(self, turn: int) -> IDisposable | None:
        return None

    def record_turn_usage(self, prompt_tokens: int, completion_tokens: int, estimated: bool) -> None:
        pass

    def record_run_outcome(self, status: str, prompt_tokens: int, completion_tokens: int) -> None:
        pass
