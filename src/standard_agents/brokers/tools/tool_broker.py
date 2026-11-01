# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Iterable

from standard_agents.brokers.tools.itool_broker import IToolBroker
from standard_agents.tools.itool import ITool


class ToolBroker(IToolBroker):
    def __init__(self, tools: Iterable[ITool]) -> None:
        # Keyed case-insensitively (C#: ToDictionary with StringComparer.OrdinalIgnoreCase), and
        # a second tool under the same name is refused, as ToDictionary refuses it.
        self._tools: dict[str, ITool] = {}

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

    # A tool that declares no way back returns None; the broker hands the natures an empty
    # string, so nothing above it has to reason about None (SPEC.md 4.9).
    async def compensate(self, name: str, input: str, outcome: str) -> str:
        compensation = await self._tool(name).compensate(input, outcome)

        return compensation if compensation is not None else ""

    # The dictionary's indexer: an absent name is a KeyError, as it is a KeyNotFoundException.
    def _tool(self, name: str) -> ITool:
        key = _fold(name)

        if key not in self._tools:
            raise KeyError(f"The given key '{name}' was not present in the dictionary.")

        return self._tools[key]


# StringComparer.OrdinalIgnoreCase: characters compared by their simple uppercase mapping.
# Python's str.upper() applies full mappings (U+00DF becomes "SS"), so each character is
# uppercased on its own and kept as it is when its mapping expands.
def _fold(value: str) -> str:
    folded: list[str] = []

    for character in value:
        candidate = character.upper()
        folded.append(candidate if len(candidate) == 1 else character)

    return "".join(folded)
