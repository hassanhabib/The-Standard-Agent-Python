# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


class IExternalToolService(ABC):
    @abstractmethod
    async def call(self, name: str, input: str) -> str: ...
