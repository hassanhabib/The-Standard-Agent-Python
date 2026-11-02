# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod

from standard_agents.models.brokers.sessions.agent_session import AgentSession


class SessionBroker(ABC):
    @abstractmethod
    async def select_session(self, session_id: str) -> AgentSession | None:
        ...

    @abstractmethod
    async def upsert_session(self, session: AgentSession) -> None:
        ...
