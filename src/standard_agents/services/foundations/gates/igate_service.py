# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


class IGateService(ABC):
    @abstractmethod
    async def screen(self, gate_prompt: str, input: str) -> str: ...
