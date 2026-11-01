# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod


# The liaison to whatever knows how to validate a document against a schema: a validator in the
# box, a full JSON Schema library, or the host's own rules.
class IContractBroker(ABC):
    # Returns None when the answer satisfies the schema, and otherwise what is wrong with it, in
    # words a model can act on, because the text becomes the reason a draft was rejected.
    @abstractmethod
    async def validate(self, answer: str, schema: str) -> str | None:
        ...
