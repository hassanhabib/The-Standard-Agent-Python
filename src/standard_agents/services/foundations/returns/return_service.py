# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.loggings.logging_broker import LoggingBroker


class ReturnService:
    """Hands the agent's final payload back to the caller."""

    def __init__(self, *, logging_broker: LoggingBroker) -> None:
        self.logging_broker = logging_broker

    async def return_payload(self, payload: str) -> str:
        return payload
