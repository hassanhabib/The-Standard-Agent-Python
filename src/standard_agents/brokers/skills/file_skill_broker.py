# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import os
import unicodedata
from typing import Sequence

from standard_agents.brokers.files.file_enumeration import enumerate_files
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.foundations.skills.skill import Skill

_FRONTMATTER_FENCE = "---"


class FileSkillBroker(SkillBroker):
    def __init__(self, skills_path: str, search_pattern: str = "*.md") -> None:
        self._skills_path = skills_path
        self._search_pattern = search_pattern

    async def select_skills(self) -> Sequence[Skill]:
        if not os.path.isdir(self._skills_path):
            return []

        skills: list[Skill] = []

        for file_path in enumerate_files(
                self._skills_path, self._search_pattern, all_directories=True):
            raw_content = _read_text_detecting_bom(file_path)

            relative_name = os.path.relpath(file_path, self._skills_path).replace("\\", "/")

            skills.append(_build_skill(relative_name, raw_content))

        return skills


def _build_skill(relative_name: str, raw_content: str) -> Skill:
    name, description, body = _parse_frontmatter(raw_content)

    return Skill(
        name=relative_name if _is_blank(name) else name,
        description=description if description is not None else "",
        content=body)


def _parse_frontmatter(content: str) -> tuple[str | None, str | None, str]:
    lines = content.replace("\r\n", "\n").split("\n")

    if not lines or _strip_dotnet_whitespace(lines[0]) != _FRONTMATTER_FENCE:
        return None, None, content

    closing_index = -1

    for index in range(1, len(lines)):
        if _strip_dotnet_whitespace(lines[index]) == _FRONTMATTER_FENCE:
            closing_index = index

            break

    if closing_index == -1:
        return None, None, content

    name = _read_field(lines, 1, closing_index, "name")
    description = _read_field(lines, 1, closing_index, "description")
    body = "\n".join(lines[closing_index + 1:]).lstrip("\n")

    return name, description, body


def _read_field(lines: list[str], start: int, end: int, key: str) -> str | None:
    prefix = key + ":"

    for index in range(start, end):
        trimmed_line = _strip_dotnet_whitespace(lines[index])

        if _starts_with_ordinal_ignore_case(trimmed_line, prefix):
            return _strip_dotnet_whitespace(trimmed_line[len(prefix):])

    return None


def _starts_with_ordinal_ignore_case(text: str, prefix: str) -> bool:
    """Mirror .NET's string.StartsWith(prefix, StringComparison.OrdinalIgnoreCase).

    Each character compares by its simple uppercase mapping.
    """
    if len(text) < len(prefix):
        return False

    return _fold_ordinal_ignore_case(text[:len(prefix)]) == _fold_ordinal_ignore_case(prefix)


def _fold_ordinal_ignore_case(value: str) -> str:
    """Uppercase each character by its simple mapping, as .NET's OrdinalIgnoreCase compares.

    A character whose Python uppercase expands to more than one character is kept as it is.
    """
    folded: list[str] = []

    for character in value:
        candidate = character.upper()
        folded.append(candidate if len(candidate) == 1 else character)

    return "".join(folded)


def _is_dotnet_whitespace(character: str) -> bool:
    """Mirror .NET's char.IsWhiteSpace.

    The Zs, Zl and Zp categories plus U+0009 to U+000D and U+0085. It differs from
    str.isspace, which also counts U+001C to U+001F.
    """
    if character in "\t\n\v\f\r\x85":
        return True

    return unicodedata.category(character) in ("Zs", "Zl", "Zp")


def _strip_dotnet_whitespace(value: str) -> str:
    """Mirror .NET's string.Trim(): remove leading and trailing .NET white space."""
    start = 0
    end = len(value)

    while start < end and _is_dotnet_whitespace(value[start]):
        start += 1

    while end > start and _is_dotnet_whitespace(value[end - 1]):
        end -= 1

    return value[start:end]


def _is_blank(text: str | None) -> bool:
    """Mirror .NET's string.IsNullOrWhiteSpace, with char.IsWhiteSpace's own set."""
    if text is None:
        return True

    return all(_is_dotnet_whitespace(character) for character in text)


def _read_text_detecting_bom(path: str) -> str:
    """Read a whole file as .NET's File.ReadAllText does.

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
