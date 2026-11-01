# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod


class ILoggingBroker(ABC):
    @abstractmethod
    async def log_information(self, message: str) -> None: ...

    @abstractmethod
    async def log_warning(self, message: str) -> None: ...

    @abstractmethod
    async def log_error(self, exception: BaseException) -> None: ...

    @abstractmethod
    async def log_critical(self, exception: BaseException) -> None: ...

    @abstractmethod
    async def log_turn(self, run_id: str, turn: int) -> None: ...

    @abstractmethod
    async def log_process(self, actor: str, message: str) -> None: ...
