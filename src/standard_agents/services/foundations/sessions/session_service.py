# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.sessions.session_broker import SessionBroker
from standard_agents.models.brokers.sessions.agent_session import AgentSession


class SessionService:
    """The conversation, as a foundation rather than as a broker reached from above.

    Coordination held the session broker directly, which meant a disk full or a permission denied
    surfaced unmapped and was attributed to the loop rather than to the store. A foundation is
    what supplies the three things that call was missing: validation, exception mapping, and
    attribution (docs/architecture-alignment.md).
    """

    def __init__(
            self,
            *,
            session_broker: SessionBroker,
            logging_broker: LoggingBroker) -> None:

        self.session_broker = session_broker
        self.logging_broker = logging_broker

    async def retrieve_session(self, session_id: str) -> AgentSession | None:
        """The conversation so far, or None when this is the first prompt in it."""
        # A conversation that has not started is not an error: None is the ordinary first
        # prompt, and it has to stay distinguishable from a failure to read.
        return await self.session_broker.select_session(session_id)

    async def record_session(self, session: AgentSession) -> None:
        """Writes the conversation back, replacing what was there."""
        raise NotImplementedError
