# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.sessions.isession_broker import ISessionBroker
from standard_agents.models.brokers.sessions.agent_session import AgentSession


# The default. SPEC.md 4.11: absent a session, behavior is exactly as if the section did not
# exist: nothing is loaded, nothing is written, and the agent is stateless prompt to prompt.
class NotConfiguredSessionBroker(ISessionBroker):
    async def select_session(self, session_id: str) -> AgentSession | None:
        return None

    async def upsert_session(self, session: AgentSession) -> None:
        return None
