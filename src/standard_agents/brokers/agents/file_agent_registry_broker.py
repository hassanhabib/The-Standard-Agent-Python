# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import os
import unicodedata
from typing import TYPE_CHECKING, Sequence

from standard_agents.brokers.agents.agent_registry_broker import AgentRegistryBroker
from standard_agents.brokers.files.file_enumeration import enumerate_files
from standard_agents.models.brokers.agents.registered_agent import RegisteredAgent

if TYPE_CHECKING:
    from standard_agents.standard_agent import StandardAgent


# The Local mode of the fleet seam: a folder where every .json document is an agent (the same
# documents StandardAgent.from_json composes), read in path order. A document's name names the
# agent (the file's own name when absent) and its description advertises it: no description,
# no advertisement, exactly like a tool.
class FileAgentRegistryBroker(AgentRegistryBroker):
    def __init__(self, agents_path: str) -> None:
        self._agents_path = agents_path

    async def select_agents(self) -> Sequence[RegisteredAgent]:
        # Imported here: StandardAgent composes this broker, so a module-level import would be
        # circular.
        from standard_agents.standard_agent import StandardAgent

        if os.path.isdir(self._agents_path) is False:
            return []

        agents: list[RegisteredAgent] = []

        # Ordinal order: UTF-16 code units, as StringComparer.Ordinal compares them.
        for document_path in sorted(
                enumerate_files(self._agents_path, "*.json", all_directories=False),
                key=lambda path: path.encode("utf-16-be", errors="surrogatepass")):
            composed: StandardAgent = StandardAgent.from_json(_read_all_text(document_path))

            agents.append(RegisteredAgent(
                name=(
                    _get_file_name_without_extension(document_path)
                    if _is_null_or_white_space(composed.name)
                    else composed.name),
                description=composed.description,
                agent=composed))

        return agents


# Path.GetFileNameWithoutExtension: the name up to its last dot, so ".json" names nothing.
def _get_file_name_without_extension(path: str) -> str:
    name = os.path.basename(path)
    dot = name.rfind(".")

    return name if dot < 0 else name[:dot]


# File.ReadAllText: the encoding a byte order mark names, UTF-8 when there is none, invalid
# sequences replaced rather than raised, line endings kept as written.
def _read_all_text(path: str) -> str:
    with open(path, "rb") as file:
        data = file.read()

    if data[:2] == b"\xfe\xff":
        return data[2:].decode("utf-16-be", errors="replace")

    if data[:4] == b"\xff\xfe\x00\x00":
        return data[4:].decode("utf-32-le", errors="replace")

    if data[:2] == b"\xff\xfe":
        return data[2:].decode("utf-16-le", errors="replace")

    if data[:3] == b"\xef\xbb\xbf":
        return data[3:].decode("utf-8", errors="replace")

    if data[:4] == b"\x00\x00\xfe\xff":
        return data[4:].decode("utf-32-be", errors="replace")

    return data.decode("utf-8", errors="replace")


# string.IsNullOrWhiteSpace, with char.IsWhiteSpace's own set.
def _is_null_or_white_space(text: str | None) -> bool:
    if text is None:
        return True

    return all(
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp")
        for character in text)
