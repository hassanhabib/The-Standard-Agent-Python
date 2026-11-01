# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class ResilienceBroker(ABC):
    @abstractmethod
    async def execute(self, operation: Callable[[], Awaitable[T]], result_type: type[T]) -> T:
        """Run the operation under this broker's policy.

        result_type names the type of the operation's result, which Python does not carry at
        run time: a broker that shapes a result of its own (a fallback) needs to know which
        protocol is asking.
        """
