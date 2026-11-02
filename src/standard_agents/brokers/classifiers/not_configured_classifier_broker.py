# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker

_ALLOW = "allow"
_NO_CONFLICT = "NONE"


class NotConfiguredClassifierBroker(ClassifierBroker):
    async def classify(self, input: str) -> str:
        return _ALLOW

    async def assess(self, system_prompt: str, input: str) -> str:
        return _NO_CONFLICT
