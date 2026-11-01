# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal


@dataclass(frozen=True)
class AgentBudget:
    """What one prompt is allowed to consume (SPEC.md 4.10).

    Any bound left None is unbounded, so a budget constrains exactly what the host chose to
    constrain and nothing else.
    """

    max_tokens: int | None = None
    max_cost_usd: Decimal | None = None
    max_wall_clock: timedelta | None = None

    # Cost per 1,000 tokens, when the host wants a cost bound rather than a token one. The
    # builder requires it to be positive whenever max_cost_usd is set: spend is the token count
    # times this rate, so a zero rate is a cost bound that can never trip.
    cost_per_thousand_tokens: Decimal = Decimal(0)

    @property
    def is_bounded(self) -> bool:
        return (
            self.max_tokens is not None
            or self.max_cost_usd is not None
            or self.max_wall_clock is not None)
