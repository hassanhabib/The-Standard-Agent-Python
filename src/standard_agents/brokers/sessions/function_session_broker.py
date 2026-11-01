# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable

from standard_agents.brokers.sessions.session_broker import SessionBroker
from standard_agents.models.brokers.sessions.agent_session import AgentSession


class FunctionSessionBroker(SessionBroker):
    """The Custom mode's substrate: host-supplied read and write, for a store the host has."""

    def __init__(
            self,
            select: Callable[[str], Awaitable[AgentSession | None]],
            upsert: Callable[[AgentSession], Awaitable[None]]) -> None:

        self._select = select
        self._upsert = upsert

    async def select_session(self, session_id: str) -> AgentSession | None:
        return await self._select(session_id)

    async def upsert_session(self, session: AgentSession) -> None:
        await self._upsert(session)
