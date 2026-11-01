# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.audits.audit_broker import AuditBroker
from standard_agents.models.brokers.audits.audit_record import AuditRecord


class NotConfiguredAuditBroker(AuditBroker):
    """The default audit sink, which writes nothing.

    SPEC.md 4.7: absent configuration no decision log is emitted, no sink is touched, and
    behavior is exactly as if the section did not exist.
    """

    async def write(self, record: AuditRecord) -> None:
        pass
