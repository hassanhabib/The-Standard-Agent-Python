# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_run_stream import AgentRunStream
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


class Agent(ABC):
    """An agent, as a host or a nested agent sees it.

    The request-rich members are the contract: a run carries a session, a caller-owned
    transcript, caller tools, resumed tool exchanges and inference controls, and ends with a
    structured outcome that says HOW it ended. The string-friendly members are adapters over
    them, so an adapter can never report a held or refused run as an answer (principal review
    2026-09-04, F-09).
    """

    @abstractmethod
    async def run_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AgentOutcome:
        """The run, in full: everything about the request that is data, and how it ended.

        Answered, refused, held on an authority, waiting on the caller, or out of turns: only
        AgentStatus.RESPONDED makes the result an answer. Setting cancellation stops the run at
        its next turn boundary, so no effect is left half-recorded (SPEC.md 4.10).
        """

    @abstractmethod
    def stream_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AsyncIterator[AgentStreamEvent]:
        """The same run, streamed (SPEC.md 4.14): every event as it happens."""

    async def process_prompt(self, prompt: str) -> str:
        """The one-line door: a prompt in, the answer's text out."""
        return (await self.run(prompt)).result

    async def run(
            self,
            request: PromptRequest | str,
            *,
            cancellation: asyncio.Event | None = None) -> AgentOutcome:
        """The run, reported with how it ended as well as what it produced.

        A plain prompt is a request that expressed no opinions. Setting cancellation stops the
        run at its next turn boundary, so no effect is left half-recorded (SPEC.md 4.10).
        Nesting reads this: AgentTool forwards the outer run's signal here, so cancelling an
        outer run stops the whole tree.
        """
        return await self.run_request(_as_request(request), cancellation=cancellation)

    def process_prompt_stream(
            self,
            request: PromptRequest | str,
            *,
            cancellation: asyncio.Event | None = None) -> AsyncIterator[AgentStreamEvent]:
        """The streamed run for a bare prompt, riding the request-rich stream."""
        return self.stream_request(_as_request(request), cancellation=cancellation)

    def run_stream(
            self,
            prompt: str,
            *,
            cancellation: asyncio.Event | None = None) -> AgentRunStream:
        """The streamed run (SPEC.md 4.14): every event live, then the structured outcome.

        One run, two readings; a caller never chooses between the answer's structure and the
        run's story. This default adapts process_prompt_stream and assumes the run answered,
        because it cannot know a pending effect or a refusal from the events alone. An
        implementation that runs the loop knows how its run ended and overrides it;
        StandardAgent does.
        """
        return AgentRunStream(
            lambda set_outcome: _adapted_stream(self, prompt, set_outcome, cancellation))


def _as_request(request: PromptRequest | str) -> PromptRequest:
    return request if isinstance(request, PromptRequest) else PromptRequest(prompt=request)


async def _adapted_stream(
        agent: Agent,
        prompt: str,
        set_outcome: Callable[[AgentOutcome], None],
        cancellation: asyncio.Event | None) -> AsyncIterator[AgentStreamEvent]:

    answer: list[str] = []

    async for stream_event in agent.process_prompt_stream(prompt, cancellation=cancellation):
        if stream_event.type is AgentStreamEventType.RESPONSE:
            answer.append(stream_event.content)

        yield stream_event

    set_outcome(AgentOutcome("".join(answer), AgentStatus.RESPONDED))
