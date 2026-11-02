# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from http import HTTPStatus
from unittest.mock import ANY, call

from standard_agents.host.models.v1.agent_run_request_v1 import AgentRunRequestV1
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType


async def _two_line_response():
    yield AgentStreamEvent(AgentStreamEventType.THINKING, "considering")
    yield AgentStreamEvent(AgentStreamEventType.RESPONSE, "line one\nline two")


async def _read(body) -> str:
    return "".join([frame async for frame in body])


async def test_should_post_stream_as_server_sent_events(
        agent,
        agents_v1_controller,
        full_request,
        expected_prompt_request):

    # given: the full request, streamed
    agent.process_prompt_stream.return_value = _two_line_response()

    # when
    actual_result = await agents_v1_controller.post_stream(full_request)
    streamed = await _read(actual_result.body)

    # then: the whole wire reached the contract; each event is one SSE frame, every content line
    # its own data line (F-11 holds on this door too)
    assert actual_result.status_code == HTTPStatus.OK
    assert actual_result.content_type == "text/event-stream"

    assert agent.mock_calls == [
        call.process_prompt_stream(expected_prompt_request, cancellation=ANY)]

    assert streamed == (
        "event: Thinking\ndata: considering\n\n"
        "event: Response\ndata: line one\ndata: line two\n\n")
