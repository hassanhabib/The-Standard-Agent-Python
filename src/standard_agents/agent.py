# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_run_stream import AgentRunStream
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.prompt_request import PromptRequest


class Agent(ABC):
    """An agent, as a host or a nested agent sees it."""

    @abstractmethod
    async def run_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AgentOutcome:
        ...

    @abstractmethod
    def stream_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AsyncIterator[AgentStreamEvent]:
        ...

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
        raise NotImplementedError

    def run_stream(
            self,
            prompt: str,
            *,
            cancellation: asyncio.Event | None = None) -> AgentRunStream:
        raise NotImplementedError


def _as_request(request: PromptRequest | str) -> PromptRequest:
    return request if isinstance(request, PromptRequest) else PromptRequest(prompt=request)
