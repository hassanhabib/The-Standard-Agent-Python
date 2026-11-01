# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Mapping, MutableMapping

from standard_agents.brokers.redactions.iredaction_broker import IRedactionBroker


# The default. SPEC.md 4.6: redaction is opt-in, and absent it the agent behaves exactly as if
# the section did not exist: no scanning, no vault, no cost.
class NotConfiguredRedactionBroker(IRedactionBroker):
    def redact(self, text: str, vault: MutableMapping[str, str]) -> str:
        return text

    def rehydrate(self, text: str, vault: Mapping[str, str]) -> str:
        return text
