# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable

from standard_agents.brokers.audits.audit_broker import AuditBroker
from standard_agents.models.brokers.audits.audit_record import AuditRecord


# The Custom mode's substrate: a host-supplied function standing in for a broker, the same shape
# FunctionGeneratorBroker gives a host-supplied brain.
class FunctionAuditBroker(AuditBroker):
    def __init__(self, write: Callable[[AuditRecord], Awaitable[None]]) -> None:
        self._write = write

    async def write(self, record: AuditRecord) -> None:
        await self._write(record)
