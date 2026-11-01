# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker


# The Custom mode of the trace: the host's own function receives every line, already written.
class FunctionLoggingBroker(ILoggingBroker):
    def __init__(self, write: Callable[[str], Awaitable[None]]) -> None:
        self.write = write

    async def log_information(self, message: str) -> None:
        await self.write(f"INFO {message}")

    async def log_warning(self, message: str) -> None:
        await self.write(f"WARNING {message}")

    async def log_error(self, exception: BaseException) -> None:
        await self.write(f"ERROR {exception}")

    async def log_critical(self, exception: BaseException) -> None:
        await self.write(f"CRITICAL {exception}")

    async def log_turn(self, run_id: str, turn: int) -> None:
        await self.write(f"Turn {turn} (run {run_id})")

    async def log_process(self, actor: str, message: str) -> None:
        await self.write(f"[{actor}] {message}")
