# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The streamed doors' frame: one server-sent event per agent stream event.

The kind is the event name so a consumer can switch on it, the content is the data. Filtering
the stream to Response events equals what the batched door returns: the parity the loop
guarantees, carried out to the protocol.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent


async def to_server_sent_events(
        stream_events: AsyncIterator[AgentStreamEvent]) -> AsyncIterator[str]:

    async for stream_event in stream_events:
        yield to_server_sent_event(stream_event)


def to_server_sent_event(stream_event: AgentStreamEvent) -> str:
    event_name = "".join(word.capitalize() for word in stream_event.type.name.split("_"))

    return f"event: {event_name}\ndata: {stream_event.content}\n\n"
