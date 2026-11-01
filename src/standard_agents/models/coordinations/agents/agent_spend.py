# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import threading
from decimal import Decimal


# What one run has consumed so far. Tokens accumulate from what providers actually reported:
# SPEC.md 3.4 forbids presenting an estimate as a measurement, so an unreported call adds
# nothing here rather than adding a guess.
class AgentSpend:
    def __init__(self) -> None:
        self._tokens = 0
        self._tokens_lock = threading.Lock()

    @property
    def tokens(self) -> int:
        with self._tokens_lock:
            return self._tokens

    def add_tokens(self, prompt_tokens: int, completion_tokens: int) -> None:
        with self._tokens_lock:
            self._tokens += prompt_tokens + completion_tokens

    def cost_usd(self, cost_per_thousand_tokens: Decimal) -> Decimal:
        return Decimal(self.tokens) / Decimal(1000) * cost_per_thousand_tokens
