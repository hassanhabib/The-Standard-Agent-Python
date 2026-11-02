# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import AsyncIterable, AsyncIterator, Callable

from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.orchestrations.agents.agent_context import AgentContext


class DecisionStream:
    """A streamed turn of thought.

    An enumeration of the turn's events that, once the enumeration completes, carries the
    context the batched door would have returned. One turn, two readings: the drafting as it
    happens, and what was decided.
    """

    def __init__(
            self,
            build: Callable[
                [Callable[[AgentContext], None]],
                AsyncIterable[AgentStreamEvent]]) -> None:

        self._result = AgentContext()
        self._events = build(self._set_result)

    @property
    def result(self) -> AgentContext:
        return self._result

    def _set_result(self, context: AgentContext) -> None:
        self._result = context

    def __aiter__(self) -> AsyncIterator[AgentStreamEvent]:
        return self._events.__aiter__()
