# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import contextvars
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

# The Python stand-in for the parts of System.Diagnostics (Activity, ActivitySource,
# ActivityListener) and System.Diagnostics.Metrics (Meter, Histogram, MeterListener) that
# ActivityTelemetryBroker uses. Python has no standard tracing library, so this is a small
# in-process recorder with the same lifecycle: a source hands out a span only while a listener
# listens to it, a started span becomes the current one, and a stopped span hands current back to
# its parent. A host (or an OpenTelemetry bridge of its own) observes through the listeners.

# Activity.Current is an AsyncLocal in .NET; a context variable is Python's equivalent.
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

    def dispose(self) -> None:
        with _registry_lock:
            if self in _activity_listeners:
                _activity_listeners.remove(self)

    def __enter__(self) -> ActivityListener:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.dispose()


class ActivitySource:
    def __init__(self, name: str) -> None:
        self.name = name

    @staticmethod
    def add_activity_listener(listener: ActivityListener) -> None:
        with _registry_lock:
            _activity_listeners.append(listener)

    def has_listeners(self) -> bool:
        return len(self._listeners()) > 0

    # None when nothing listens to this source: an unobserved source costs nothing.
    def start_activity(self, name: str) -> Activity | None:
        listeners = self._listeners()

        if len(listeners) == 0:
            return None

        activity = Activity(name, self, _current_activity.get())
        _current_activity.set(activity)

        for listener in listeners:
            if listener.activity_started is not None:
                listener.activity_started(activity)

        return activity

    def _listeners(self) -> list[ActivityListener]:
        with _registry_lock:
            listeners = list(_activity_listeners)

        return [listener for listener in listeners if listener.should_listen_to(self)]


class Activity:
    def __init__(self, operation_name: str, source: ActivitySource, parent: Activity | None) -> None:
        self.operation_name = operation_name
        self.display_name = operation_name
        self.source = source
        self.parent = parent
        self.tags: dict[str, Any] = {}
        self.start_time_utc = datetime.now(timezone.utc)
        self.duration = timedelta(0)
        self.is_stopped = False

    @staticmethod
    def current() -> Activity | None:
        return _current_activity.get()

    # A None value removes the tag, as SetTag(key, null) does.
    def set_tag(self, key: str, value: Any) -> Activity:
        if value is None:
            self.tags.pop(key, None)
        else:
            self.tags[key] = value

        return self

    def get_tag_item(self, key: str) -> Any:
        return self.tags.get(key)

    # Stop() once: the duration is fixed, listeners hear of it, and the parent is current again.
    def stop(self) -> None:
        if self.is_stopped:
            return

        self.is_stopped = True
        self.duration = datetime.now(timezone.utc) - self.start_time_utc

        for listener in self.source._listeners():
            if listener.activity_stopped is not None:
                listener.activity_stopped(self)

        _current_activity.set(self.parent)

    def dispose(self) -> None:
        self.stop()

    def __enter__(self) -> Activity:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.dispose()


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

    def dispose(self) -> None:
        with _registry_lock:
            if self in _meter_listeners:
                _meter_listeners.remove(self)

    def __enter__(self) -> MeterListener:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.dispose()


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

    # A measurement nobody listens to goes nowhere.
    def record(self, value: int | float, *tags: tuple[str, Any]) -> None:
        with _registry_lock:
            listeners = list(_meter_listeners)

        for listener in listeners:
            if listener.should_listen_to(self):
                listener.measurement_recorded(self, value, dict(tags))
