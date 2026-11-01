# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""A protocol server on the other end of a process's standard streams, in memory.

Every line the broker writes is recorded, and every line the script answers is queued for the
broker to read. The script may answer a line with nothing (a notification), or with several
lines (a server that speaks before it answers).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Iterable
from typing import Any

Respond = Callable[[Any], Iterable[str]]


class ScriptedStdioServer:
    """output is the server's standard output and input its standard input, as the broker sees
    them; lines is every line the broker wrote, without its line break."""

    def __init__(self, respond: Respond) -> None:
        self._respond = respond
        self._server_lines: asyncio.Queue[str | None] = asyncio.Queue()
        self.output = _QueueReader(self._server_lines)
        self.input = _RecordingWriter(self)
        self.lines: list[str] = []

    def end(self) -> None:
        self._server_lines.put_nowait(None)

    def _receive(self, line: str) -> None:
        self.lines.append(line)

        for answer in self._respond(json.loads(line)):
            self._server_lines.put_nowait(answer)


class _QueueReader:
    """asyncio.StreamReader.readline over the queued lines: b"" once the server has ended."""

    def __init__(self, lines: asyncio.Queue[str | None]) -> None:
        self._lines = lines

    async def readline(self) -> bytes:
        line = await self._lines.get()

        return b"" if line is None else (line + "\n").encode("utf-8")


class _RecordingWriter:
    """asyncio.StreamWriter.write and drain, recording each line the broker writes."""

    def __init__(self, server: ScriptedStdioServer) -> None:
        self._server = server

    def write(self, data: bytes) -> None:
        text = data.decode("utf-8")

        if not text.endswith("\n"):
            raise NotImplementedError("The broker writes whole lines.")

        self._server._receive(text[:-1])

    async def drain(self) -> None:
        pass
