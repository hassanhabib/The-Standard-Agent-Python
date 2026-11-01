# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from standard_agents.tools.tool import Tool


class RememberTool(Tool):
    def __init__(self, remember: Callable[[str], Awaitable[None]]) -> None:
        self._remember = remember

    @property
    def name(self) -> str:
        raise NotImplementedError

    async def execute(self, input: str) -> str:
        fact = _extract_fact(input)
        await self._remember(fact)

        return f"Remembered: {fact}"


def _extract_fact(input: str) -> str:
    try:
        arguments = json.loads(input)
    except json.JSONDecodeError:
        return input

    if isinstance(arguments, dict) and isinstance(arguments.get("fact"), str):
        return arguments["fact"]

    return input
