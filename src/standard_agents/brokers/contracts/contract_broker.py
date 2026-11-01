# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod


class ContractBroker(ABC):
    """The liaison to whatever knows how to validate a document against a schema.

    A validator in the box, a full JSON Schema library, or the host's own rules.
    """

    @abstractmethod
    async def validate(self, answer: str, schema: str) -> str | None:
        """Returns None when the answer satisfies the schema, otherwise what is wrong with it.

        The problem is said in words a model can act on, because the text becomes the reason a
        draft was rejected.
        """
