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
        raise NotImplementedError

    async def run(
            self,
            request: PromptRequest | str,
            *,
            cancellation: asyncio.Event | None = None) -> AgentOutcome:
        raise NotImplementedError

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
