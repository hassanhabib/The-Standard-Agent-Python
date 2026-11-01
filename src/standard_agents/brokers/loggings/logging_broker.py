# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod

from standard_agents.models.loggings.agent_step import AgentStep


class LoggingBroker(ABC):
    @abstractmethod
    async def log_information(self, message: str) -> None:
        ...

    @abstractmethod
    async def log_trace(self, message: str) -> None:
        ...

    @abstractmethod
    async def log_debug(self, message: str) -> None:
        ...

    @abstractmethod
    async def log_warning(self, message: str) -> None:
        ...

    @abstractmethod
    async def log_error(self, exception: BaseException) -> None:
        ...

    @abstractmethod
    async def log_critical(self, exception: BaseException) -> None:
        ...

    @abstractmethod
    async def log_reset(self) -> None:
        ...

    @abstractmethod
    async def log_turn(self, turn: int) -> None:
        ...

    @abstractmethod
    async def log_outcome(self, message: str) -> None:
        ...

    @abstractmethod
    async def log_step(self, step: AgentStep) -> None:
        ...

    @abstractmethod
    async def log_process(self, actor: str, message: str, detail: bool = False) -> None:
        ...

    async def log_payload(self, actor: str, summary: str, payload: str, detail: bool) -> None:
        """Logs a process event that carries a payload.

        The payload is the prompt, the system prompt, the Brain's reply, a tool's input or
        output. The summary says what happened; the payload is the content, kept apart so a sink
        can decide what it keeps (principal review 2026-09-04, F-14). A broker that does not
        distinguish the two logs them as one message.
        """
        await self.log_process(actor, f"{summary} → {payload}", detail)
