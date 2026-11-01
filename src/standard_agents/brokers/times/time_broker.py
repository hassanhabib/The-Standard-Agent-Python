# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from datetime import datetime, timezone

from standard_agents.brokers.times.itime_broker import ITimeBroker


class TimeBroker(ITimeBroker):
    # DateTimeOffset.UtcNow: an aware datetime at offset zero.
    def get_current_date_time_offset(self) -> datetime:
        return datetime.now(timezone.utc)
