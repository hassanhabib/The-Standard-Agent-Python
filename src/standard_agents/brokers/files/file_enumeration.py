# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Directory.EnumerateFiles, as .NET performs it, for the brokers that enumerate a folder. Not a
# broker: the one place the search-pattern grammar and the walk order live, so every broker that
# lists files lists the same ones in the same order.

from __future__ import annotations

import os
from collections import deque
from functools import lru_cache
from typing import Iterator

# The wildcards of a translated Win32 expression (FileSystemName.TranslateWin32Expression).
_STAR = "*"
_DOS_STAR = "<"
_DOS_QM = ">"
_DOS_DOT = '"'


# Lazily, as Directory.EnumerateFiles does: each path is the folder joined to the file's name,
# a folder's files are yielded before any folder beneath it is entered, and folders beneath are
# entered in the order they were found (breadth first). A folder that is a link is not entered.
def enumerate_files(path: str, search_pattern: str, all_directories: bool) -> Iterator[str]:
    directory, expression = _normalize_inputs(path, search_pattern)
    tokens = _tokenize(expression)
    ignore_case = os.name == "nt"
    pending: deque[str] = deque([directory])

    while pending:
        current = pending.popleft()

        with os.scandir(current) as entries:
            for entry in entries:
                if entry.is_dir():
                    if all_directories and entry.is_symlink() is False:
                        pending.append(os.path.join(current, entry.name))

                    continue

                if _matches(tokens, entry.name, ignore_case):
                    yield os.path.join(current, entry.name)


# FileSystemEnumerableFactory.NormalizeInputs: a folder named inside the pattern moves into the
# path, and the Win32 expression is translated to its wildcard grammar.
def _normalize_inputs(directory: str, expression: str) -> tuple[str, str]:
    if os.path.isabs(expression) or os.path.splitdrive(expression)[0] != "":
        raise ValueError(
            "Second path fragment must not be a drive or UNC name. (Parameter 'expression')")

    directory_name = os.path.dirname(expression)

    if len(directory_name) != 0:
        directory = os.path.join(directory, directory_name)
        expression = expression[len(directory_name) + 1:]

    if expression == "*":
        return directory, expression

    if expression in ("", ".", "*.*"):
        return directory, "*"

    return directory, expression


# A token is (is_wildcard, character). On Windows '<', '>' and '"' cannot appear in a name and
# act as the DOS wildcards they translate to; elsewhere they, and '\', are escaped to literals.
def _tokenize(expression: str) -> tuple[tuple[bool, str], ...]:
    dos_wildcards_are_literal = os.sep != "\\"
    tokens: list[tuple[bool, str]] = []
    length = len(expression)

    for index, character in enumerate(expression):
        if character == ".":
            if index >= 1 and index == length - 1 and expression[index - 1] == "*":
                tokens[-1] = (True, _DOS_STAR)
            elif index < length - 1 and expression[index + 1] in "?*":
                tokens.append((True, _DOS_DOT))
            else:
                tokens.append((False, "."))
        elif character == "?":
            tokens.append((True, _DOS_QM))
        elif character == "*":
            tokens.append((True, _STAR))
        elif character in '<>"':
            tokens.append((not dos_wildcards_are_literal, character))
        else:
            tokens.append((False, character))

    return tuple(tokens)


# FileSystemName.MatchesWin32Expression over the translated expression: '*' matches any run of
# characters; '<' any run that does not pass the name's final period; '>' any one character,
# or nothing at a period or at the end; '"' a period, or nothing at the end.
def _matches(tokens: tuple[tuple[bool, str], ...], name: str, ignore_case: bool) -> bool:
    if tokens == ((True, _STAR),):
        return True

    folded_name = _fold(name) if ignore_case else name
    last_period = name.rfind(".")

    @lru_cache(maxsize=None)
    def match(token_index: int, name_index: int) -> bool:
        if token_index == len(tokens):
            return name_index == len(name)

        is_wildcard, character = tokens[token_index]
        name_finished = name_index == len(name)

        if is_wildcard is False:
            if name_finished:
                return False

            expected = _fold(character) if ignore_case else character

            return (folded_name[name_index] == expected
                and match(token_index + 1, name_index + 1))

        if character == _STAR:
            return any(
                match(token_index + 1, index)
                for index in range(name_index, len(name) + 1))

        if character == _DOS_STAR:
            index = name_index

            while True:
                if match(token_index + 1, index):
                    return True

                if index == len(name):
                    return False

                if index == last_period:
                    return match(token_index + 1, index + 1)

                index += 1

        if character == _DOS_QM:
            if name_finished or name[name_index] == ".":
                next_index = token_index

                while next_index < len(tokens) and tokens[next_index] == (True, _DOS_QM):
                    next_index += 1

                return match(next_index, name_index)

            return match(token_index + 1, name_index + 1)

        # DOS_DOT
        if name_finished:
            return match(token_index + 1, name_index)

        return name[name_index] == "." and match(token_index + 1, name_index + 1)

    return match(0, 0)


# Ordinal ignore-case: each character by its simple uppercase mapping, kept as it is when its
# mapping expands.
def _fold(text: str) -> str:
    folded: list[str] = []

    for character in text:
        candidate = character.upper()
        folded.append(candidate if len(candidate) == 1 else character)

    return "".join(folded)
