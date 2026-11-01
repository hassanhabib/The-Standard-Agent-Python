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

# A JSON SCHEMA, not example JSON. The wire validates this strictly: a hosted provider rejects
# the WHOLE request when any advertised tool's parameters is not a schema of type object, which
# made every native run against a strict endpoint fail the moment memory was composed in. Found
# by the first production consumer, not by any scripted test, because scripted brokers accept
# anything.
_PARAMETERS = (
    '{"type":"object","properties":{"fact":{"type":"string",'
    + '"description":"the fact to remember"}},"required":["fact"]}')

_DESCRIPTION = (
    "Store a fact to remember across sessions. Use it when the user tells you "
    + "something worth keeping \u2014 their name, where they are, their preferences.")


class _RemembersMemories(Protocol):
    """What the obsolete form was handed: something with a remember routine, a memory service."""

    async def remember(self, memory: str) -> None:
        ...


class RememberTool(Tool):
    """The built-in remember tool: the agent's way to store a fact across sessions.

    It holds a function, not the memory service. A tool is reached through the tool broker,
    underneath the foundations, so a tool that KEEPS a service re-enters the tier stack from
    below it. The tool holds the same shape a host-authored tool holds: a function it was handed.
    """

    def __init__(self, remember: Callable[[str], Awaitable[None]] | _RemembersMemories) -> None:
        # The converting alias, kept so nothing written against an earlier release breaks (the
        # same pattern as local_brain to on_brain): it accepts the service and keeps only its
        # routine.
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
        return "remember"

    @property
    def description(self) -> str:
        return _DESCRIPTION

    @property
    def parameters(self) -> str:
        return _PARAMETERS

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
