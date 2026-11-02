# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from datetime import datetime, timezone

from standard_agents.brokers.telemetries.activities import Activity, ActivitySource, Meter
from standard_agents.brokers.telemetries.telemetry_broker import TelemetryScope, TelemetryBroker

SOURCE_NAME = "Standard.Agents"

_activity_source = ActivitySource(SOURCE_NAME)
_meter = Meter(SOURCE_NAME)
_token_usage = _meter.create_histogram("gen_ai.client.token.usage", unit="{token}")
_operation_duration = _meter.create_histogram("gen_ai.client.operation.duration", unit="s")


class ActivityTelemetryBroker(TelemetryBroker):
    """The in-box telemetry broker: OpenTelemetry-compatible spans and metrics.

    Recorded through the in-process recorder in activities.py, which mirrors .NET's
    ActivitySource and Meter, with no packages, no exporter, no dependency. A process that adds
    a listener for the Standard.Agents source picks everything up; a process that adds nothing
    pays nothing, because an unobserved source hands back None instead of a span. Attribute and
    metric names follow the OpenTelemetry GenAI semantic conventions, so a collector that
    already understands agents understands this one.
    """

    SOURCE_NAME = SOURCE_NAME

    def __init__(self, agent_name: str = "standard-agent") -> None:
        self._agent_name = agent_name

    def start_run(self, session_id: str) -> TelemetryScope | None:
        run = _activity_source.start_activity(f"invoke_agent {self._agent_name}")

        if run is not None:
            run.set_tag("gen_ai.operation.name", "invoke_agent")
            run.set_tag("gen_ai.agent.name", self._agent_name)

        if session_id and run is not None:
            run.set_tag("gen_ai.conversation.id", session_id)

        return run

    def start_turn(self, turn: int) -> TelemetryScope | None:
        turn_activity = _activity_source.start_activity(f"turn {turn}")

        if turn_activity is not None:
            turn_activity.set_tag("standard.agents.turn.index", turn)

        return turn_activity

    def record_turn_usage(
            self,
            prompt_tokens: int,
            completion_tokens: int,
            estimated: bool) -> None:

        # Only a span this source opened is annotated: the ambient current activity may belong
        # to the host when nothing is listening here, and another library's span is not ours to
        # write on.
        current = Activity.current()

        if current is not None and current.source is _activity_source:
            current.set_tag("gen_ai.usage.input_tokens", prompt_tokens)
            current.set_tag("gen_ai.usage.output_tokens", completion_tokens)
            current.set_tag("standard.agents.usage.estimated", estimated)

        _token_usage.record(prompt_tokens, ("gen_ai.token.type", "input"))
        _token_usage.record(completion_tokens, ("gen_ai.token.type", "output"))

    def record_run_outcome(self, status: str, prompt_tokens: int, completion_tokens: int) -> None:
        current = Activity.current()

        if current is not None and current.source is _activity_source:
            current.set_tag("standard.agents.run.status", status)
            current.set_tag("gen_ai.usage.input_tokens", prompt_tokens)
            current.set_tag("gen_ai.usage.output_tokens", completion_tokens)

            _operation_duration.record(
                (datetime.now(timezone.utc) - current.start_time).total_seconds(),
                ("gen_ai.operation.name", "invoke_agent"),
                ("standard.agents.run.status", status))
