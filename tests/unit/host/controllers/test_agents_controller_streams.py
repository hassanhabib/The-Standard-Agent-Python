# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from http import HTTPStatus
from unittest.mock import ANY, call

import pytest

from standard_agents.host.models.agent_run_request import AgentRunRequest
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType


async def _two_events():
    yield AgentStreamEvent(AgentStreamEventType.THINKING, "considering")
    yield AgentStreamEvent(AgentStreamEventType.NARRATION, "let me check...")
    yield AgentStreamEvent(AgentStreamEventType.RESPONSE, "the answer")


async def _read(body) -> str:
    return "".join([frame async for frame in body])


async def test_should_post_stream_as_server_sent_events(agent, agents_controller):
    # given
    agent.process_prompt_stream.return_value = _two_events()

    # when
    actual_result = await agents_controller.post_stream(AgentRunRequest(prompt="what is owed"))
    streamed = await _read(actual_result.body)

    # then: each event arrives as SSE, its kind as the event name, its content as data
    assert actual_result.status_code == HTTPStatus.OK
    assert actual_result.content_type == "text/event-stream"
    assert "event: Thinking" in streamed
    assert "data: considering" in streamed
    assert "event: Narration" in streamed
    assert "data: let me check..." in streamed
    assert "event: Response" in streamed
    assert "data: the answer" in streamed
    assert agent.mock_calls == [call.process_prompt_stream("what is owed", cancellation=ANY)]


async def _one_response(content: str):
    yield AgentStreamEvent(AgentStreamEventType.RESPONSE, content)


# Found in the 2026-09-04 principal review (F-11): the event's content was written into ONE data
# line. Server-sent events end an event at a blank line and take every line as a field, so a
# multi-line answer, the normal case, produced an unprefixed second line and a truncated event.
# The spec's shape is one "data:" line per line of content; the consumer joins them back with a
# newline. CR, LF and CRLF all end a line in SSE, so all three split.
@pytest.mark.parametrize("content", [
    "line one\nline two",
    "line one\r\nline two",
    "line one\rline two",
])
async def test_should_frame_every_line_of_content_as_data_on_post_stream(
        agent,
        agents_controller,
        content):

    # given
    agent.process_prompt_stream.return_value = _one_response(content)

    # when
    actual_result = await agents_controller.post_stream(AgentRunRequest(prompt="what is owed"))
    streamed = await _read(actual_result.body)

    # then: one event, every content line carried as its own data line
    assert streamed == "event: Response\ndata: line one\ndata: line two\n\n"


# Content that happens to look like a field must stay data. Without the per-line prefix a model
# answer beginning "event: " or "data: " on its own line rewrites the frame the consumer is
# reading.
async def test_should_keep_field_shaped_content_as_data_on_post_stream(agent, agents_controller):
    # given
    agent.process_prompt_stream.return_value = _one_response(
        "event: Forged\ndata: injected\n\nevent: Forged")

    # when
    actual_result = await agents_controller.post_stream(AgentRunRequest(prompt="what is owed"))
    streamed = await _read(actual_result.body)

    # then: every line is data, the blank line inside the content does not end the event
    assert streamed == (
        "event: Response\n"
        "data: event: Forged\n"
        "data: data: injected\n"
        "data: \n"
        "data: event: Forged\n"
        "\n")
