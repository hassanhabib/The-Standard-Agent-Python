# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass


# What the decision log may carry. payloads False, the default, records metadata: the event,
# the actor, the time, the principal, and the length and hash of any payload, never the payload
# itself. True records the payloads too, as the configured redaction leaves them. A deliberate
# opt-in, because an audit sink usually has broader access and a longer life than anything at
# runtime (principal review 2026-09-04, F-14).
@dataclass(frozen=True)
class AuditPolicy:
    payloads: bool

    # C# exposes this as the static property AuditPolicy.Metadata, a new instance per read.
    @staticmethod
    def metadata() -> AuditPolicy:
        return AuditPolicy(payloads=False)
