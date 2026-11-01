# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Awaitable, Callable, Sequence


# The host's selection judgment (SPEC.md 4.15): given the run's task and the described tool
# names, the subset this run is offered. A model carrying a delegate rather than a naked
# delegate parameter, because configuration crosses natures where a dependency may not.
class ToolSelector:
    def __init__(
            self,
            select: Callable[[str, Sequence[str]], Awaitable[Sequence[str]]]) -> None:
        self._select = select

    async def select_async(
            self,
            task: str,
            described_tool_names: Sequence[str]) -> Sequence[str]:
        return await self._select(task, described_tool_names)
