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

import re
from collections.abc import AsyncIterator

from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent

# CR, LF and CRLF all end a line in server-sent events; CRLF first so it splits as one.
_LINE_TERMINATORS = re.compile(r"\r\n|\n|\r")


async def to_server_sent_events(
        stream_events: AsyncIterator[AgentStreamEvent]) -> AsyncIterator[str]:

    async for stream_event in stream_events:
        yield to_server_sent_event(stream_event)


def to_server_sent_event(stream_event: AgentStreamEvent) -> str:
    """One frame, in the shape the SSE specification reads.

    The kind as the event name, one "data:" line per line of content, then the blank line that
    ends the event. A content line left unprefixed is read as a field, and a blank line inside
    the content ends the event early, which is what a multi-line answer, the normal case, used
    to do (principal review 2026-09-04, F-11). The consumer joins the data lines back with a
    newline.
    """
    event_name = "".join(word.capitalize() for word in stream_event.type.name.split("_"))
    content_lines = _LINE_TERMINATORS.split(stream_event.content)

    frame = [f"event: {event_name}\n"]
    frame.extend(f"data: {content_line}\n" for content_line in content_lines)
    frame.append("\n")

    return "".join(frame)
