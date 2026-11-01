# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import json
import warnings
from collections.abc import Awaitable, Callable
from typing import Protocol

from standard_agents.tools.tool import Tool


class _RemembersMemories(Protocol):
    """What the obsolete form was handed: something with a remember routine, a memory service."""

    async def remember(self, memory: str) -> None:
        ...


class RememberTool(Tool):
    def __init__(self, remember: Callable[[str], Awaitable[None]] | _RemembersMemories) -> None:
        if not callable(remember):
            warnings.warn(
                "Pass the remember routine itself: a tool holds a function, not a service. "
                + "This alias keeps working.",
                DeprecationWarning,
                stacklevel=2)

            remember = remember.remember

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
