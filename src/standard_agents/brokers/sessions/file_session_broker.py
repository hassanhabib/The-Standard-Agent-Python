# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import Any

from standard_agents.brokers.sessions.db_concurrency_exception import DBConcurrencyException
from standard_agents.brokers.sessions.isession_broker import ISessionBroker
from standard_agents.models.brokers.sessions.agent_session import AgentSession

# JsonSerializerOptions.MaxDepth's default.
_MAX_DEPTH = 64

# Utf8JsonWriter's indentation: two spaces per level.
_INDENT = "  "

# The characters JavaScriptEncoder.Default escapes even inside Basic Latin.
_HTML_SENSITIVE = frozenset('"&\'+<>`')

_SHORT_ESCAPES = {
    "\\": "\\\\",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
}


# The Local mode: one JSON file per session in a folder.
#
# Written to a temporary file and moved into place, so a crash mid-write leaves the previous
# session intact rather than a half-written one. A session is the thing resumption depends on;
# corrupting it while saving it would defeat the feature at exactly the moment it is needed.
#
# It is a real store rather than an in-memory one on purpose: SPEC.md 4.11 requires resumption
# to work from a DIFFERENT process, and an in-memory session cannot demonstrate that.
class FileSessionBroker(ISessionBroker):
    def __init__(self, sessions_path: str) -> None:
        self._sessions_path = os.path.abspath(sessions_path)

        # One lock over reads and writes alike: a move over a file another prompt is reading
        # fails on Windows with access denied, which is how two prompts in one session crashed a
        # run (principal review 2026-09-04, F-06). Per instance: a second process gets its own
        # lock, which is the limit of a file and the reason a store shared across replicas is a
        # session broker of its own.
        self._file_lock = threading.Lock()

    async def select_session(self, session_id: str) -> AgentSession | None:
        with self._file_lock:
            return _read_session(self._file_for(session_id))

    # Compare-and-swap on the version, a file's stand-in for a store's own: a write based on a
    # read that is no longer current is refused with the concurrency failure the foundation
    # localizes, rather than erasing the turn a faster writer stored.
    async def upsert_session(self, session: AgentSession) -> None:
        with self._file_lock:
            os.makedirs(self._sessions_path, exist_ok=True)

            session_file = self._file_for(session.id)
            stored_session = _read_session(session_file)
            stored_version = 0 if stored_session is None else stored_session.version

            if session.version != stored_version + 1:
                raise DBConcurrencyException(
                    f"Session '{session.id}' is at version {stored_version}; this write was "
                    + f"based on version {session.version - 1}.")

            temporary_file = f"{session_file}.writing"

            with open(temporary_file, "w", encoding="utf-8", newline="") as writer:
                writer.write(_serialize_indented(session.to_json_dict(), depth=0))

            os.replace(temporary_file, session_file)

    # A session id comes from the host and may be anything: an email, a ticket reference, a
    # path fragment. Hashing it keeps it off the filesystem's grammar entirely rather than
    # trying to sanitize a name that could escape the folder. Lowercase hex, which is
    # load-bearing: a session written by one implementation must be found by the other.
    def _file_for(self, session_id: str) -> str:
        safe_name = hashlib.sha256(_utf8_bytes(session_id)).hexdigest()[:32]

        return os.path.join(self._sessions_path, f"{safe_name}.json")


def _read_session(session_file: str) -> AgentSession | None:
    if os.path.isfile(session_file) is False:
        return None

    data = _parse(_read_all_text(session_file))

    return None if data is None else AgentSession.from_json_dict(data)


# Encoding.UTF8.GetBytes: a lone surrogate encodes as U+FFFD, where Python's encoder would raise.
def _utf8_bytes(value: str) -> bytes:
    utf16 = value.encode("utf-16-le", errors="surrogatepass")

    return utf16.decode("utf-16-le", errors="replace").encode("utf-8")


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


def _reject_constant(constant: str) -> Any:
    raise ValueError(f"'{constant}' is an invalid JSON literal.")


# JsonSerializer.Deserialize: strict JSON, no NaN or Infinity, nesting no deeper than 64.
def _parse(text: str) -> Any:
    node = json.loads(text, parse_constant=_reject_constant)
    _ensure_depth(node, depth=0)

    return node


def _ensure_depth(node: Any, depth: int) -> None:
    if isinstance(node, (dict, list)):
        depth += 1

        if depth > _MAX_DEPTH:
            raise ValueError(f"The maximum configured depth of {_MAX_DEPTH} has been exceeded.")

        children = node.values() if isinstance(node, dict) else node

        for child in children:
            _ensure_depth(child, depth)


# JsonSerializer.Serialize with WriteIndented: two spaces per level, "name": value, every member
# and element on its own line, an empty object or array as {} or [], lines ended by the
# platform's line ending, written with JavaScriptEncoder.Default.
def _serialize_indented(node: Any, depth: int) -> str:
    if node is None:
        return "null"

    if node is True:
        return "true"

    if node is False:
        return "false"

    if isinstance(node, (int, float)):
        return json.dumps(node)

    if isinstance(node, str):
        return _escape(node)

    inner = os.linesep + _INDENT * (depth + 1)
    closing = os.linesep + _INDENT * depth

    if isinstance(node, (list, tuple)):
        if len(node) == 0:
            return "[]"

        return "[" + inner + ("," + inner).join(
            _serialize_indented(item, depth + 1) for item in node) + closing + "]"

    if isinstance(node, dict):
        if len(node) == 0:
            return "{}"

        return "{" + inner + ("," + inner).join(
            _escape(key) + ": " + _serialize_indented(value, depth + 1)
            for key, value in node.items()) + closing + "}"

    raise TypeError(f"Cannot write {type(node).__name__} as JSON.")


# JavaScriptEncoder.Default: printable Basic Latin passes except the HTML-sensitive characters;
# everything else is escaped, as \uXXXX in upper-case hex, surrogate pairs as two escapes.
def _escape(text: str) -> str:
    parts = ['"']

    for character in text:
        code = ord(character)

        if character in _SHORT_ESCAPES:
            parts.append(_SHORT_ESCAPES[character])
        elif 0x20 <= code <= 0x7E and character not in _HTML_SENSITIVE:
            parts.append(character)
        elif code > 0xFFFF:
            code -= 0x10000
            parts.append(f"\\u{0xD800 + (code >> 10):04X}")
            parts.append(f"\\u{0xDC00 + (code & 0x3FF):04X}")
        else:
            parts.append(f"\\u{code:04X}")

    parts.append('"')

    return "".join(parts)
