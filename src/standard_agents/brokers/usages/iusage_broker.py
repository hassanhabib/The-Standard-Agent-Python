# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod


# The liaison to whatever knows how to count tokens: a tokenizer in the box, a provider's own
# counting endpoint, or a vocabulary shipped with a model.
class IUsageBroker(ABC):
    # How many tokens the given text occupies. Returns 0 for empty text.
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        ...
