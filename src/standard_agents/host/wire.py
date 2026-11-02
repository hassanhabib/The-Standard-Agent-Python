# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The host's JSON wire, read and written as ASP.NET's web serializer reads and writes it.

The C# host binds and answers with System.Text.Json under JsonSerializerDefaults.Web: property
names camelCased from the C# names and matched ignoring case on the way in, numbers readable from
strings, unknown properties ignored, null values written, and every character outside printable
ASCII (and the HTML-sensitive ones) escaped. The host's models are dataclasses whose fields are
the C# properties snake_cased, so the names are derived here the way the serializer derives them
from the C# names, and each field's annotation says what the JSON value must be.
"""

from __future__ import annotations

import dataclasses
import json
import math
import re
import typing
from collections.abc import Iterable
from enum import Enum
from types import NoneType, UnionType
from typing import Any

_JSON_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_JSON_INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)")
_INT32_RANGE = range(-2**31, 2**31)

_SHORT_ESCAPES = {
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
    "\\": "\\\\",
}

# Printable ASCII the default JavaScriptEncoder still escapes, because each means something in
# HTML or in a script.
_HTML_SENSITIVE = frozenset("\"&'+<>`")


class JsonReadError(Exception):
    """A document the serializer could not read, named by its JSON path as the serializer names
    it ($, $.history, $.history[0].prompt)."""

    def __init__(self, path: str, message: str) -> None:
        super().__init__(message)
        self.path = path
        self.message = message


def read_model(model_type: type, text: str) -> Any:
    """Read a document into a model, or None for the JSON literal null.

    A property set to null is read as None whatever the field says, as the serializer reads
    null into a non-nullable reference; refusing it is model validation's, not the reader's.
    """
    try:
        document = json.loads(
            text,
            object_pairs_hook=_JsonObject,
            parse_float=_JsonNumber,
            parse_int=_JsonNumber,
            parse_constant=_refuse_constant)
    except ValueError as error:
        raise JsonReadError("$", f"{error}. Path: $.") from error

    if document is None:
        return None

    return _read(model_type, document, "$")


def write_json(value: Any) -> str:
    """Write a model, a list or a dictionary as the web serializer writes it."""
    return "".join(_write(value))


def csharp_name(field_name: str) -> str:
    """The C# property a field ports: session_id is SessionId."""
    return "".join(word.capitalize() for word in field_name.split("_"))


def json_name(field_name: str) -> str:
    """The property's name on the wire, camelCased as the web serializer writes it."""
    words = field_name.split("_")

    return words[0] + "".join(word.capitalize() for word in words[1:])


class _JsonObject:
    """A JSON object as written: its properties in order, a repeated name kept, the last one
    read last, as the serializer reads them."""

    def __init__(self, pairs: list[tuple[str, Any]]) -> None:
        self.pairs = pairs


class _JsonNumber:
    """A JSON number as written, so a field reads it with the C# type's own rules."""

    def __init__(self, text: str) -> None:
        self.text = text


def _refuse_constant(name: str) -> Any:
    raise ValueError(f"'{name}' is an invalid JSON literal")


def _read(hint: Any, value: Any, path: str) -> Any:
    if value is None:
        return None

    nullable_hint = _without_none(hint)

    if nullable_hint is not hint:
        return _read(nullable_hint, value, path)

    if hint is str:
        if isinstance(value, str):
            return value

    elif hint is bool:
        if isinstance(value, bool):
            return value

    elif hint is float:
        number = _number_text(value)

        if number is not None and _JSON_NUMBER.fullmatch(number):
            parsed = float(number)

            if math.isfinite(parsed):
                return parsed

    elif hint is int:
        number = _number_text(value)

        if number is not None and _JSON_INTEGER.fullmatch(number) and int(number) in _INT32_RANGE:
            return int(number)

    elif typing.get_origin(hint) is tuple:
        if isinstance(value, list):
            item_hint = typing.get_args(hint)[0]

            return tuple(
                _read(item_hint, item, f"{path}[{index}]")
                for index, item in enumerate(value))

    elif dataclasses.is_dataclass(hint):
        if isinstance(value, _JsonObject):
            return _read_dataclass(hint, value, path)

    raise JsonReadError(
        path,
        f"The JSON value could not be converted to {_csharp_type_name(hint)}. Path: {path}.")


def _read_dataclass(model_type: type, document: _JsonObject, path: str) -> Any:
    hints = typing.get_type_hints(model_type)
    fields = {_upper(json_name(field.name)): field for field in dataclasses.fields(model_type)}
    arguments: dict[str, Any] = {}

    for name, value in document.pairs:
        field = fields.get(_upper(name))

        if field is not None:
            arguments[field.name] = _read(hints[field.name], value, f"{path}.{name}")

    # A positional record parameter the document leaves out is default(T), which is null; an
    # init property keeps its initializer, which the field's default carries.
    for field in dataclasses.fields(model_type):
        if field.name not in arguments and _has_no_default(field):
            arguments[field.name] = None

    return model_type(**arguments)


def _write(value: Any) -> Iterable[str]:
    if value is None:
        yield "null"
    elif isinstance(value, bool):
        yield "true" if value else "false"
    elif isinstance(value, Enum):
        yield str(value.value)
    elif isinstance(value, int):
        yield str(value)
    elif isinstance(value, str):
        yield _escape(value)
    elif dataclasses.is_dataclass(value):
        yield from _write_object(
            (json_name(field.name), getattr(value, field.name))
            for field in dataclasses.fields(value))
    elif isinstance(value, dict):
        yield from _write_object(value.items())
    elif isinstance(value, (list, tuple)):
        yield "["

        for index, item in enumerate(value):
            if index:
                yield ","

            yield from _write(item)

        yield "]"
    else:
        raise TypeError(f"{type(value).__name__} has no JSON form on the host's wire")


def _write_object(properties: Iterable[tuple[str, Any]]) -> Iterable[str]:
    yield "{"

    for index, (name, value) in enumerate(properties):
        if index:
            yield ","

        yield _escape(name)
        yield ":"
        yield from _write(value)

    yield "}"


def _escape(text: str) -> str:
    """A JSON string as JavaScriptEncoder.Default escapes it: '<' is \\u003C, 'e' acute is
    \\u00E9, and a character beyond the BMP is its two UTF-16 halves."""
    escaped = ['"']

    for character in text:
        code = ord(character)

        if character in _SHORT_ESCAPES:
            escaped.append(_SHORT_ESCAPES[character])
        elif 0x20 <= code < 0x7F and character not in _HTML_SENSITIVE:
            escaped.append(character)
        elif code > 0xFFFF:
            code -= 0x10000
            escaped.append(f"\\u{0xD800 + (code >> 10):04X}\\u{0xDC00 + (code & 0x3FF):04X}")
        else:
            escaped.append(f"\\u{code:04X}")

    escaped.append('"')

    return "".join(escaped)


def _number_text(value: Any) -> str | None:
    """A number's text, from a number or, as the web defaults allow, from a string."""
    if isinstance(value, _JsonNumber):
        return value.text

    if isinstance(value, str):
        return value

    return None


def _without_none(hint: Any) -> Any:
    """X for X | None; the hint itself otherwise."""
    if typing.get_origin(hint) in (typing.Union, UnionType):
        arguments = [argument for argument in typing.get_args(hint) if argument is not NoneType]

        if len(arguments) == 1:
            return arguments[0]

    return hint


def _has_no_default(field: dataclasses.Field) -> bool:
    return (
        field.default is dataclasses.MISSING
        and field.default_factory is dataclasses.MISSING)


def _upper(name: str) -> str:
    # Property names match ignoring case, as OrdinalIgnoreCase compares them.
    return name.upper()


def _csharp_type_name(hint: Any) -> str:
    """The C# type a field ports, as the serializer names it in an error."""
    nullable_hint = _without_none(hint)

    if nullable_hint is not hint:
        name = _csharp_type_name(nullable_hint)

        return f"System.Nullable`1[{name}]" if nullable_hint in (bool, int, float) else name

    if typing.get_origin(hint) is tuple:
        item_name = _csharp_type_name(typing.get_args(hint)[0])

        return f"System.Collections.Generic.IReadOnlyList`1[{item_name}]"

    if dataclasses.is_dataclass(hint):
        # standard_agents.host.models.v1 is Standard.Agents.Host.Models.V1.
        namespace = ".".join(
            word.capitalize()
            for part in hint.__module__.split(".")[:-1]
            for word in part.split("_"))

        return f"{namespace}.{hint.__name__}"

    return {
        str: "System.String",
        bool: "System.Boolean",
        int: "System.Int32",
        float: "System.Double",
    }[hint]
