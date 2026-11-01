# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""A small in-process span and metric recorder with .NET's System.Diagnostics lifecycle.

The Python stand-in for the parts of System.Diagnostics (Activity, ActivitySource,
ActivityListener) and System.Diagnostics.Metrics (Meter, Histogram, MeterListener) that
ActivityTelemetryBroker uses. Python has no standard tracing library, so this is a small
in-process recorder with the same lifecycle: a source hands out a span only while a listener
listens to it, a started span becomes the current one, and a stopped span hands current back to
its parent. A host (or an OpenTelemetry bridge of its own) observes through the listeners.
"""

from __future__ import annotations

import contextvars
import threading
import time
from datetime import datetime, timedelta, timezone
from collections.abc import Callable
from types import TracebackType
from typing import Any

# The current span flows with the async context, as Activity.Current does in .NET.
_current_activity: contextvars.ContextVar[Activity | None] = contextvars.ContextVar(
    "standard_agents_current_activity",
    default=None)

_registry_lock = threading.Lock()
_activity_listeners: list[ActivityListener] = []
_meter_listeners: list[MeterListener] = []


class ActivityListener:
    def __init__(
            self,
            should_listen_to: Callable[[ActivitySource], bool],
            activity_started: Callable[[Activity], None] | None = None,
            activity_stopped: Callable[[Activity], None] | None = None) -> None:

        self.should_listen_to = should_listen_to
        self.activity_started = activity_started
        self.activity_stopped = activity_stopped

    def close(self) -> None:
        with _registry_lock:
            if self in _activity_listeners:
                _activity_listeners.remove(self)

    def __enter__(self) -> ActivityListener:
        return self

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None) -> None:

        self.close()


class ActivitySource:
    def __init__(self, name: str) -> None:
        self.name = name

    @staticmethod
    def add_activity_listener(listener: ActivityListener) -> None:
        with _registry_lock:
            _activity_listeners.append(listener)

    def has_listeners(self) -> bool:
        return bool(self._listeners())

    def start_activity(self, name: str) -> Activity | None:
        """Start a span as the current one, or return None when nothing listens to this source.

        An unobserved source costs nothing.
        """
        listeners = self._listeners()

        if not listeners:
            return None

        activity = Activity(name, self, _current_activity.get())
        activity._current_token = _current_activity.set(activity)

        for listener in listeners:
            if listener.activity_started is not None:
                listener.activity_started(activity)

        return activity

    def _listeners(self) -> list[ActivityListener]:
        with _registry_lock:
            listeners = list(_activity_listeners)

        return [listener for listener in listeners if listener.should_listen_to(self)]


class Activity:
    def __init__(
            self,
            operation_name: str,
            source: ActivitySource,
            parent: Activity | None) -> None:

        self.operation_name = operation_name
        self.display_name = operation_name
        self.source = source
        self.parent = parent
        self.tags: dict[str, Any] = {}
        self.start_time = datetime.now(timezone.utc)
        self.duration = timedelta(0)
        self.is_stopped = False

        # The duration is measured on the monotonic clock, so a wall-clock change mid-span
        # cannot stretch it or make it negative.
        self._started_counter = time.perf_counter()

        # Set by ActivitySource.start_activity when the span becomes the current one; stop()
        # resets it to hand current back to the parent.
        self._current_token: contextvars.Token[Activity | None] | None = None

    @staticmethod
    def current() -> Activity | None:
        return _current_activity.get()

    def set_tag(self, key: str, value: Any) -> Activity:
        """Set a tag; a None value removes it, as .NET's SetTag(key, null) does."""
        if value is None:
            self.tags.pop(key, None)
        else:
            self.tags[key] = value

        return self

    def get_tag(self, key: str) -> Any:
        return self.tags.get(key)

    def stop(self) -> None:
        """Stop the span, once.

        The duration is fixed, listeners hear of it, and the parent is current again. A second
        call does nothing.
        """
        if self.is_stopped:
            return

        self.is_stopped = True
        self.duration = timedelta(seconds=time.perf_counter() - self._started_counter)

        for listener in self.source._listeners():
            if listener.activity_stopped is not None:
                listener.activity_stopped(self)

        if self._current_token is None:
            # Never made current (constructed directly rather than started by a source).
            _current_activity.set(self.parent)
        else:
            _current_activity.reset(self._current_token)

    def close(self) -> None:
        self.stop()

    def __enter__(self) -> Activity:
        return self

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None) -> None:

        self.close()


class MeterListener:
    def __init__(
            self,
            should_listen_to: Callable[[Histogram], bool],
            measurement_recorded: Callable[[Histogram, int | float, dict[str, Any]], None]) -> None:

        self.should_listen_to = should_listen_to
        self.measurement_recorded = measurement_recorded

    def start(self) -> None:
        with _registry_lock:
            _meter_listeners.append(self)

    def close(self) -> None:
        with _registry_lock:
            if self in _meter_listeners:
                _meter_listeners.remove(self)

    def __enter__(self) -> MeterListener:
        return self

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None) -> None:

        self.close()


class Meter:
    def __init__(self, name: str) -> None:
        self.name = name

    def create_histogram(self, name: str, unit: str | None = None) -> Histogram:
        return Histogram(self, name, unit)


class Histogram:
    def __init__(self, meter: Meter, name: str, unit: str | None) -> None:
        self.meter = meter
        self.name = name
        self.unit = unit

    def record(self, value: int | float, *tags: tuple[str, Any]) -> None:
        """Hand the measurement to every listener of this histogram.

        A measurement nobody listens to goes nowhere.
        """
        with _registry_lock:
            listeners = list(_meter_listeners)

        for listener in listeners:
            if listener.should_listen_to(self):
                listener.measurement_recorded(self, value, dict(tags))
