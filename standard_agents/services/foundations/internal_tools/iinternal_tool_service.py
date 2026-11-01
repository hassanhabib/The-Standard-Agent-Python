# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


class IInternalToolService(ABC):
    @abstractmethod
    async def handles(self, name: str) -> bool: ...
