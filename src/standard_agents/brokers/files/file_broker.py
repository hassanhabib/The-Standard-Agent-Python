# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Iterable, Sequence


class SearchOption(Enum):
    """Whether a file search stays in the folder or descends into every folder beneath it.

    Mirrors System.IO.SearchOption.
    """

    TOP_DIRECTORY_ONLY = 0
    ALL_DIRECTORIES = 1


class FileBroker(ABC):
    @abstractmethod
    def directory_exists(self, path: str) -> bool:
        ...

    @abstractmethod
    def select_files(
            self,
            path: str,
            search_pattern: str,
            search_option: SearchOption) -> Sequence[str]:
        ...

    @abstractmethod
    async def read_file(self, path: str) -> str:
        ...

    @abstractmethod
    def read_file_sync(self, path: str) -> str:
        """The synchronous twin of read_file, for callers that cannot await."""

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        ...

    @abstractmethod
    async def read_all_lines(self, path: str) -> Sequence[str]:
        ...

    @abstractmethod
    def create_directory(self, path: str) -> None:
        ...

    @abstractmethod
    async def append_all_lines(self, path: str, lines: Iterable[str]) -> None:
        ...
