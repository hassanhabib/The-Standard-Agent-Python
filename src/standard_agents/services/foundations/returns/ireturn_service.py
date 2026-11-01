# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


class IReturnService(ABC):
    @abstractmethod
    async def return_payload(self, payload: str) -> str: ...
