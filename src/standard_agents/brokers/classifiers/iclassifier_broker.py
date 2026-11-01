# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


# What the Gate screens with: text in, a verdict out ("allow", or "refuse: <reason>").
class IClassifierBroker(ABC):
    @abstractmethod
    async def classify(self, text: str) -> str: ...
