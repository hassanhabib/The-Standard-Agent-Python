# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod

from standard_agents.models.brokers.audits.audit_record import AuditRecord


class IAuditBroker(ABC):
    @abstractmethod
    async def write(self, record: AuditRecord) -> None:
        ...
