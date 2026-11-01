# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MISSING = object()


# Wire names follow JsonNamingPolicy.CamelCase; reads are case-insensitive and null values are
# omitted on write (WhenWritingNull), as the HttpMcpBroker's serializer options leave them.
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
            uri=_as_string(_read(data, "uri")),
            text=_as_string(_read(data, "text")))


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

        resource = _read(data, "resource")

        return cls(
            type=_as_string(_read(data, "type")),
            text=_as_string(_read(data, "text")),
            resource=(
                None if resource is _MISSING or resource is None
                else EmbeddedResource.from_json_dict(resource)),
            uri=_as_string(_read(data, "uri")),
            name=_as_string(_read(data, "name")),
            mime_type=_as_string(_read(data, "mimeType")))


# PropertyNameCaseInsensitive: every key matching ignoring case is read, the last one wins.
def _read(data: dict, name: str) -> Any:
    found = _MISSING

    for key, value in data.items():
        if key.lower() == name.lower():
            found = value

    return found


# An absent constructor parameter is default(string), which is null.
def _as_string(value: Any) -> str | None:
    if value is _MISSING or value is None:
        return None

    if isinstance(value, str):
        return value

    raise ValueError("The JSON value could not be converted to System.String.")
