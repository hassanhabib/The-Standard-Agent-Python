# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Awaitable, Callable

from standard_agents.tools.tool import Tool


class RememberTool(Tool):
    def __init__(self, remember: Callable[[str], Awaitable[None]]) -> None:
        self._remember = remember

    @property
    def name(self) -> str:
        raise NotImplementedError

    async def execute(self, input: str) -> str:
        raise NotImplementedError
