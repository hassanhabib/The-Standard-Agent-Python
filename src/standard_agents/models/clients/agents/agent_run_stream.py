# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import AsyncIterable, AsyncIterator, Callable

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


class AgentRunStream:
    """The streamed run (SPEC.md 4.14).

    An enumeration of the run's events that, once the enumeration completes, carries the same
    structured outcome the batched door returns. One run, two readings: the events as they
    happen, and how it ended.
    """

    def __init__(
            self,
            build: Callable[
                [Callable[[AgentOutcome], None]],
                AsyncIterable[AgentStreamEvent]]) -> None:

        # How the run ended, defined once the enumeration completes (SPEC.md 4.14). Before that
        # it reads as a failed run, exactly the seed the batched door starts from.
        self._outcome = AgentOutcome("", AgentStatus.FAILED)
        self._events = build(self._set_outcome)

    @property
    def outcome(self) -> AgentOutcome:
        return self._outcome

    def _set_outcome(self, outcome: AgentOutcome) -> None:
        self._outcome = outcome

    def __aiter__(self) -> AsyncIterator[AgentStreamEvent]:
        return self._events.__aiter__()
