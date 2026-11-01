# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent


@dataclass(frozen=True)
class _Ended:
    """The last item a run writes: how its events ended, and the fault when it faulted."""

    exception: BaseException | None


class RunEvents:
    """The run's events, on their way from the loop to whoever reads them.

    The loop runs in a task of its own and writes here; the door it entered by reads. The
    capacity is one event, so the run is never more than one event ahead of its reader, as the
    C# loop is over its bounded channel. Reading it is iterating it: the iteration ends when the
    run completes, and raises the run's fault when the run faulted.

    A reader that stops reading abandons the events. A write already waiting for room is then
    cancelled, and every later write is refused the same way, so the run stops at its next event
    instead of waiting for a reader that is gone.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[AgentStreamEvent | _Ended] = asyncio.Queue(maxsize=1)
        self._is_abandoned = False
        self._waiting_writer: asyncio.Task | None = None

    async def write(self, event: AgentStreamEvent) -> None:
        if self._is_abandoned:
            raise asyncio.CancelledError()

        await self._put(event)

    async def complete(self, exception: BaseException | None = None) -> None:
        """End the events, with the run's fault when it faulted. Nobody is told once abandoned."""
        if self._is_abandoned:
            return

        await self._put(_Ended(exception))

    def abandon(self) -> None:
        self._is_abandoned = True

        if self._waiting_writer is not None:
            self._waiting_writer.cancel()

    def __aiter__(self) -> RunEvents:
        return self

    async def __anext__(self) -> AgentStreamEvent:
        item = await self._queue.get()

        if not isinstance(item, _Ended):
            return item

        if item.exception is not None:
            raise item.exception

        raise StopAsyncIteration

    async def _put(self, item: AgentStreamEvent | _Ended) -> None:
        self._waiting_writer = asyncio.current_task()

        try:
            await self._queue.put(item)
        finally:
            self._waiting_writer = None
