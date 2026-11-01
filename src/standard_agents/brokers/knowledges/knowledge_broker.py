# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence


class KnowledgeBroker(ABC):
    @abstractmethod
    async def select_knowledge(self, query: str) -> Sequence[str]:
        ...
