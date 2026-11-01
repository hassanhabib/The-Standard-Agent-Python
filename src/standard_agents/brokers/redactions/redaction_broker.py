# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping


class RedactionBroker(ABC):
    @abstractmethod
    def redact(self, text: str, vault: MutableMapping[str, str]) -> str:
        ...

    @abstractmethod
    def rehydrate(self, text: str, vault: Mapping[str, str]) -> str:
        ...
