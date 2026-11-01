# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import json
import os
from typing import Any

from standard_agents.brokers.effects.effect_ledger_broker import EffectLedgerBroker
from standard_agents.models.brokers.effects.effect_record import EffectRecord

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
_DATE_TIME_OFFSET_KEYS = frozenset({"claimedOn", "leaseUntil", "recordedOn"})


class FileEffectLedgerBroker(EffectLedgerBroker):
    """The Local mode of the ledger: one JSON file per act, in a folder.

    Run-once survives the process (SPEC.md 4.9). Local and single-process by design: the atomic
    claim is the file system's create-new, which one machine honours; a fleet shares a ledger
    through use_effect_ledger.
    """

    def __init__(self, ledger_path: str) -> None:
        self._ledger_path = os.path.abspath(ledger_path)

    async def insert_claim(self, claim: EffectRecord) -> bool:
        """Claims and writes in one step.

        Create-new refuses a key that already has a file, which is exactly what run-once needs to
        know, and the record is written into the file so created.
        """
        os.makedirs(self._ledger_path, exist_ok=True)

        try:
            with open(self._file_for(claim.idempotency_key), "xb") as file:
                file.write(_serialize(claim.to_json_dict()).encode("utf-8"))

            return True
        except PermissionError:
            # UnauthorizedAccessException is not an IOException, so it is not caught.
            raise
        except OSError:
            return False

    async def select_record(self, idempotency_key: str) -> EffectRecord | None:
        file = self._file_for(idempotency_key)

        if not os.path.isfile(file):
            return None

        data = _parse(_read_all_text(file))

        return None if data is None else EffectRecord.from_json_dict(data)

    async def update_record(self, record: EffectRecord) -> None:
        """Writes the record aside and moves it into place.

        A crash mid-write leaves the previous record standing rather than a half-written one
        that would read as a different act.
        """
        os.makedirs(self._ledger_path, exist_ok=True)
        file = self._file_for(record.idempotency_key)
        temporary_file = f"{file}.writing"

        with open(temporary_file, "w", encoding="utf-8", newline="") as writer:
            writer.write(_serialize(record.to_json_dict()))

        os.replace(temporary_file, file)

    async def delete_record(self, idempotency_key: str) -> None:
        file = self._file_for(idempotency_key)

        # File.Delete: a missing file is not an error, a missing folder is.
        try:
            os.remove(file)
        except FileNotFoundError:
            if os.path.isdir(os.path.dirname(file)):
                return

            raise

    def _file_for(self, idempotency_key: str) -> str:
        """The record's file, named by its key.

        The key is already a hash (SPEC.md 4.9 requires it derived, never supplied), so it is a
        safe file name as it stands.
        """
        return os.path.join(self._ledger_path, f"{idempotency_key}.json")


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
