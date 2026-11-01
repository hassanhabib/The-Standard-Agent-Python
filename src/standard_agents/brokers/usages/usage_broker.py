# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod


class UsageBroker(ABC):
    """The liaison to whatever knows how to count tokens.

    A tokenizer in the box, a provider's own counting endpoint, or a vocabulary shipped with a
    model.
    """

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """How many tokens the given text occupies. Returns 0 for empty text."""
