# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class AgentUsage:
    """
    What one model call consumed.

    prompt_tokens: tokens sent, the system prompt, observations and the user message.
    completion_tokens: tokens the model produced in reply.
    is_estimated: False when the provider reported these numbers itself, True when they were
    counted locally. A budget can be enforced on either, but only a reported number can be
    reconciled against an invoice, so the distinction travels with the number rather than being
    inferred from which brain happened to be configured.
    """

    prompt_tokens: int
    completion_tokens: int
    is_estimated: bool

    # A call that consumed nothing: the identity for accumulation.
    EMPTY: ClassVar[AgentUsage]

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


AgentUsage.EMPTY = AgentUsage(prompt_tokens=0, completion_tokens=0, is_estimated=False)
