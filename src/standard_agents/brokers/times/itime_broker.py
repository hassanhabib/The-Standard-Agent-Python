# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class ITimeBroker(ABC):
    @abstractmethod
    def get_current_date_time_offset(self) -> datetime:
        ...
