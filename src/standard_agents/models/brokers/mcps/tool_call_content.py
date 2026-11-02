# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The content items a tools/call result carries.

Wire names follow JsonNamingPolicy.CamelCase; reads are case-insensitive and null values are
omitted on write (WhenWritingNull), as the HttpMcpBroker's serializer options leave them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MISSING = object()


@dataclass(frozen=True)
class EmbeddedResource:
    uri: str | None
    text: str | None

    def to_json_dict(self) -> dict:
        values = {
            "uri": self.uri,
            "text": self.text,
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> EmbeddedResource:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to EmbeddedResource.")

        return cls(
            uri=_as_string(_read_ignoring_case(data, "uri")),
            text=_as_string(_read_ignoring_case(data, "text")))


@dataclass(frozen=True)
class ToolCallContent:
    type: str
    text: str | None
    resource: EmbeddedResource | None
    uri: str | None
    name: str | None
    mime_type: str | None

    def to_json_dict(self) -> dict:
        values = {
            "type": self.type,
            "text": self.text,
            "resource": None if self.resource is None else self.resource.to_json_dict(),
            "uri": self.uri,
            "name": self.name,
            "mimeType": self.mime_type,
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> ToolCallContent:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ToolCallContent.")

        resource = _read_ignoring_case(data, "resource")

        return cls(
            type=_as_string(_read_ignoring_case(data, "type")),
            text=_as_string(_read_ignoring_case(data, "text")),
            resource=(
                None if resource is _MISSING or resource is None
                else EmbeddedResource.from_json_dict(resource)),
            uri=_as_string(_read_ignoring_case(data, "uri")),
            name=_as_string(_read_ignoring_case(data, "name")),
            mime_type=_as_string(_read_ignoring_case(data, "mimeType")))


def _read_ignoring_case(data: dict, name: str) -> Any:
    """Read a property the way PropertyNameCaseInsensitive does.

    Every key that matches the name ignoring case is read, and the last one wins.
    """
    found = _MISSING

    for key, value in data.items():
        if key.lower() == name.lower():
            found = value

    return found


def _as_string(value: Any) -> str | None:
    """Read a JSON string, reading an absent or null value as None.

    An absent constructor parameter is default(string), which is null.
    """
    if value is _MISSING or value is None:
        return None

    if isinstance(value, str):
        return value

    raise ValueError("The JSON value could not be converted to System.String.")
