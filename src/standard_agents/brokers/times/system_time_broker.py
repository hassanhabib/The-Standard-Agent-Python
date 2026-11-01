# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from datetime import datetime, timezone

from standard_agents.brokers.times.time_broker import TimeBroker


class SystemTimeBroker(TimeBroker):
    def get_current_date_time(self) -> datetime:
        """The current time as an aware datetime at offset zero (DateTimeOffset.UtcNow)."""
        return datetime.now(timezone.utc)
