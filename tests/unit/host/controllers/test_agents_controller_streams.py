# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from http import HTTPStatus
from unittest.mock import ANY, call

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
