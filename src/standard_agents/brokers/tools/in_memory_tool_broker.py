# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Iterable

from standard_agents.brokers.tools.tool_broker import ToolBroker
from standard_agents.tools.tool import Tool


class InMemoryToolBroker(ToolBroker):
    def __init__(self, tools: Iterable[Tool]) -> None:
        # Keyed case-insensitively (StringComparer.OrdinalIgnoreCase), and a second tool under
        # the same name is refused, as ToDictionary refuses it.
        self._tools: dict[str, Tool] = {}

        for tool in tools:
            key = _fold(tool.name)

            if key in self._tools:
                raise ValueError(
                    f"An item with the same key has already been added. Key: {tool.name}")

            self._tools[key] = tool

    async def has(self, name: str) -> bool:
        return _fold(name) in self._tools

    async def run(self, name: str, input: str) -> str:
        return await self._tool(name).execute(input)

    async def compensate(self, name: str, input: str, outcome: str) -> str:
        """Undoes a tool's act, returning what was done, or "" when the tool declares no way back.

        A tool that cannot be undone returns None; the broker hands the natures an empty string,
        so nothing above it has to reason about None (SPEC.md 4.9).
        """
        compensation = await self._tool(name).compensate(input, outcome)

        return compensation if compensation is not None else ""

    def _tool(self, name: str) -> Tool:
        """The tool under this name; an absent name is a KeyError (KeyNotFoundException)."""
        key = _fold(name)

        if key not in self._tools:
            raise KeyError(f"The given key '{name}' was not present in the dictionary.")

        return self._tools[key]


def _fold(value: str) -> str:
    """Folds a name for comparison as StringComparer.OrdinalIgnoreCase does.

    Each character is compared by its simple uppercase mapping. Python's str.upper() applies full
    mappings (U+00DF becomes "SS"), so each character is uppercased on its own and kept as it is
    when its mapping expands.
    """
    folded: list[str] = []

    for character in value:
        candidate = character.upper()
        folded.append(candidate if len(candidate) == 1 else character)

    return "".join(folded)
