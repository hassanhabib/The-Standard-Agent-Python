# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.classifiers.iclassifier_broker import IClassifierBroker


# No Gate configured: every request is let through, exactly as if the Gate were absent.
class NotConfiguredClassifierBroker(IClassifierBroker):
    async def classify(self, text: str) -> str:
        return "allow"
