# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import threading
import unicodedata
from collections.abc import Iterable
from typing import Any

from standard_agents.brokers.audits.audit_broker import AuditBroker
from standard_agents.models.brokers.audits.audit_record import AuditRecord

# JsonSerializerOptions.MaxDepth's default.
_MAX_DEPTH = 64

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

# The members the record writes as a DateTimeOffset. Utf8JsonWriter formats a DateTimeOffset
# itself and never passes it through the encoder, so its '+' is written as it is.
_DATE_TIME_OFFSET_KEYS = frozenset({"timestamp"})

# StreamReader.ReadLine: a line ends at CR, LF or CRLF.
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


class FileAuditBroker(AuditBroker):
    """The decision log's file sink: one JSON object per line (SPEC.md 4.7).

    The broker owns three sink mechanics and no business flow: it appends, it serializes
    concurrent writers, and it chains hashes. The chain lives here because only the sink knows
    what the previous record on THIS sink was.

    Each write appends and closes rather than holding the file open. A decision log is read while
    it is being written (by a tail, a shipper, a test) and a retained write handle locks those
    readers out on Windows. The cost of reopening is paid once per record and buys a sink
    anything can read at any moment.
    """

    def __init__(self, audit_path: str) -> None:
        self._audit_path = os.path.abspath(audit_path)
        self._write_lock = threading.Lock()
        self._chain_seeded = False
        self._previous_hash: str | None = None

    async def write(self, record: AuditRecord) -> None:
        # One writer at a time. Records from concurrent runs may interleave, but a record is
        # never interleaved into (SPEC.md 4.7).
        with self._write_lock:
            self._seed_chain()

            chained_record = dataclasses.replace(record, previous_hash=self._previous_hash)
            line = _serialize(chained_record.to_json_dict())

            # Append, never truncate. This is the durability rule (SPEC.md 4.7); there is
            # deliberately no code path in this broker that can shorten the sink.
            with open(self._audit_path, "a", encoding="utf-8", newline="") as file:
                file.write(line + os.linesep)

            self._previous_hash = _hash(line)

    @staticmethod
    def find_broken_link(lines: Iterable[str]) -> int | None:
        """Verifies a sink written by this broker.

        Every record's previous_hash must equal the hash of the line before it. Returns the
        1-based line number of the first record that does not, or None when the chain is intact,
        so a caller can prove no record in the MIDDLE of a decision log was altered or removed
        (SPEC.md 4.7).

        What it does not prove, said plainly (principal review 2026-09-04, F-13): a suffix cut
        off the end leaves a valid prefix with no broken link, and the chain is unkeyed, so anyone
        who can rewrite the file can recompute it. This is local, append-only, hash-linked
        evidence, not immutable audit storage. A regulated deployment anchors the terminal hash
        somewhere it cannot write, or keeps the sink on append-only storage.
        """
        expected_hash: str | None = None

        for line_number, line in enumerate(lines, start=1):
            if _is_blank(line):
                continue

            data = _parse(line)
            record = None if data is None else AuditRecord.from_json_dict(data)
            previous_hash = None if record is None else record.previous_hash

            if previous_hash != expected_hash:
                return line_number

            expected_hash = _hash(line)

        return None

    def _seed_chain(self) -> None:
        """Continues an existing sink's chain rather than restarting it.

        A process restart then does not read as tampering. Done once, on the first write,
        because the sink may not exist yet when the broker is constructed.
        """
        if self._chain_seeded:
            return

        self._chain_seeded = True

        directory = os.path.dirname(self._audit_path)

        if directory:
            os.makedirs(directory, exist_ok=True)

        if not os.path.isfile(self._audit_path):
            return

        last_line: str | None = None

        for line in _read_lines(self._audit_path):
            if not _is_blank(line):
                last_line = line

        self._previous_hash = None if last_line is None else _hash(last_line)


def _hash(line: str) -> str:
    """The line's SHA-256 in lowercase hex.

    Lowercase is load-bearing: the chain one implementation wrote must verify on the other.
    """
    return hashlib.sha256(_utf8_bytes(line)).hexdigest()


def _utf8_bytes(value: str) -> bytes:
    """Encodes as .NET's Encoding.UTF8.GetBytes: a lone surrogate becomes U+FFFD.

    Python's own encoder would raise on it.
    """
    utf16 = value.encode("utf-16-le", errors="surrogatepass")

    return utf16.decode("utf-16-le", errors="replace").encode("utf-8")


def _read_lines(path: str) -> list[str]:
    """Reads a file's lines as .NET's File.ReadLines does.

    The encoding a byte order mark names, UTF-8 when there is none, split at CR, LF or CRLF, with
    no empty line after a final line break.
    """
    text = _read_all_text(path)

    if not text:
        return []

    lines = _LINE_BREAK.split(text)

    if lines[-1] == "":
        lines.pop()

    return lines


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


def _reject_constant(constant: str) -> Any:
    raise ValueError(f"'{constant}' is an invalid JSON literal.")


def _parse(text: str) -> Any:
    """Parses as JsonSerializer.Deserialize: strict JSON, no NaN or Infinity, depth at most 64."""
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


def _serialize(node: Any) -> str:
    """Writes compact JSON as JsonSerializer.Serialize does with JavaScriptEncoder.Default."""
    if node is None:
        return "null"

    # Identity, not truthiness: True and False are ints too, and 1 or 0 must stay numbers.
    if node is True:
        return "true"

    if node is False:
        return "false"

    if isinstance(node, (int, float)):
        return json.dumps(node)

    if isinstance(node, str):
        return _escape(node)

    if isinstance(node, (list, tuple)):
        return "[" + ",".join(_serialize(item) for item in node) + "]"

    if isinstance(node, dict):
        return "{" + ",".join(
            _escape(key) + ":" + (
                f'"{value}"' if key in _DATE_TIME_OFFSET_KEYS and isinstance(value, str)
                else _serialize(value))
            for key, value in node.items()) + "}"

    raise TypeError(f"Cannot write {type(node).__name__} as JSON.")


def _escape(text: str) -> str:
    """Quotes and escapes a string as JavaScriptEncoder.Default does.

    Printable Basic Latin passes except the HTML-sensitive characters; everything else is
    escaped, as \\uXXXX in upper-case hex, surrogate pairs as two escapes.
    """
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
