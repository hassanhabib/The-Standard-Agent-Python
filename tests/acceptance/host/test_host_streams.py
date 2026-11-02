# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import ANY, call

from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType


async def _two_line_response():
    yield AgentStreamEvent(AgentStreamEventType.THINKING, "considering")
    yield AgentStreamEvent(AgentStreamEventType.RESPONSE, "line one\nline two")


async def test_should_stream_server_sent_events_through_http(
        agent,
        serve_host,
        full_request_document,
        expected_prompt_request):

    # given: the V1 request on the streamed door
    agent.process_prompt_stream.return_value = _two_line_response()

    async with serve_host() as client:
        # when
        response = await client.post_json("api/V1/agents/streams", full_request_document)

    # then: the SSE content type on the wire, one frame per event, one data line per content
    # line (F-11), and the whole request reached the contract
    assert response.status == 200
    assert response.media_type == "text/event-stream"

    assert response.text == (
        "event: Thinking\ndata: considering\n\n"
        "event: Response\ndata: line one\ndata: line two\n\n")

    assert agent.process_prompt_stream.call_args_list == [
        call(expected_prompt_request, cancellation=ANY)]
