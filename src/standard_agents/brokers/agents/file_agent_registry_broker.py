# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import os
import unicodedata
from collections.abc import Sequence
from typing import TYPE_CHECKING

from standard_agents.brokers.agents.agent_registry_broker import AgentRegistryBroker
from standard_agents.brokers.files.file_enumeration import enumerate_files
from standard_agents.models.brokers.agents.registered_agent import RegisteredAgent

if TYPE_CHECKING:
    from standard_agents.standard_agent import StandardAgent


class FileAgentRegistryBroker(AgentRegistryBroker):
    """The Local mode of the fleet seam: a folder where every .json document is an agent.

    The documents are the same ones StandardAgent.from_json composes, read in path order. A
    document's name names the agent (the file's own name when absent) and its description
    advertises it: no description, no advertisement, exactly like a tool.
    """

    def __init__(self, agents_path: str) -> None:
        self._agents_path = agents_path

    async def select_agents(self) -> Sequence[RegisteredAgent]:
        # Imported here: StandardAgent composes this broker, so a module-level import would be
        # circular.
        from standard_agents.standard_agent import StandardAgent

        if not os.path.isdir(self._agents_path):
            return []

        # Ordinal order: UTF-16 code units, as StringComparer.Ordinal compares them.
        document_paths = sorted(
            enumerate_files(self._agents_path, "*.json", all_directories=False),
            key=lambda path: path.encode("utf-16-be", errors="surrogatepass"))

        agents: list[RegisteredAgent] = []

        for document_path in document_paths:
            composed: StandardAgent = StandardAgent.from_json(_read_all_text(document_path))

            agents.append(RegisteredAgent(
                name=(
                    _name_without_extension(document_path)
                    if _is_blank(composed.name)
                    else composed.name),
                description=composed.description,
                agent=composed))

        return agents


def _name_without_extension(path: str) -> str:
    """The file's name up to its last dot, so ".json" names nothing.

    Mirrors Path.GetFileNameWithoutExtension, which os.path.splitext does not: splitext keeps a
    leading-dot name whole.
    """
    name = os.path.basename(path)
    dot = name.rfind(".")

    return name if dot < 0 else name[:dot]


def _read_all_text(path: str) -> str:
    """Reads a file as .NET's File.ReadAllText does.

    The encoding a byte order mark names, UTF-8 when there is none, invalid sequences replaced
    rather than raised, line endings kept as written.
    """
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


def _is_blank(text: str | None) -> bool:
    """True for None, empty, or all whitespace, as .NET's string.IsNullOrWhiteSpace decides.

    The whitespace set is char.IsWhiteSpace's (Zs, Zl, Zp, U+0009 to U+000D and U+0085), which
    differs from str.isspace on U+001C to U+001F.
    """
    if text is None:
        return True

    return all(
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp")
        for character in text)
