# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import os
import re
from typing import Iterable, Sequence

from standard_agents.brokers.files.file_enumeration import enumerate_files
from standard_agents.brokers.files.ifile_broker import IFileBroker, SearchOption

# StreamReader.ReadLine: a line ends at CR, LF or CRLF.
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


class FileBroker(IFileBroker):
    def directory_exists(self, path: str) -> bool:
        return os.path.isdir(path)

    def select_files(
            self,
            path: str,
            search_pattern: str,
            search_option: SearchOption) -> Sequence[str]:

        return list(enumerate_files(
            path,
            search_pattern,
            all_directories=search_option is SearchOption.ALL_DIRECTORIES))

    async def read_file(self, path: str) -> str:
        return _read_all_text(path)

    def read_file_sync(self, path: str) -> str:
        return _read_all_text(path)

    def file_exists(self, path: str) -> bool:
        return os.path.isfile(path)

    async def read_all_lines(self, path: str) -> Sequence[str]:
        text = _read_all_text(path)

        if text == "":
            return []

        lines = _LINE_BREAK.split(text)

        if lines[-1] == "":
            lines.pop()

        return lines

    def create_directory(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    # File.AppendAllLines: each line followed by the platform's line ending, UTF-8 without a
    # byte order mark, the file created when it does not exist.
    async def append_all_lines(self, path: str, lines: Iterable[str]) -> None:
        with open(path, "a", encoding="utf-8", newline="") as file:
            for line in lines:
                file.write(line + os.linesep)


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
