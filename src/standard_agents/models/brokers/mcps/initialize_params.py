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
class ClientInfo:
    name: str
    version: str

    def to_json_dict(self) -> dict:
        values = {
            "name": self.name,
            "version": self.version,
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> ClientInfo:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ClientInfo.")

        return cls(
            name=_as_string(_read(data, "name")),
            version=_as_string(_read(data, "version")))


@dataclass(frozen=True)
class InitializeParams:
    protocol_version: str

    # A JsonObject in C#: kept as the parsed JSON object it is.
    capabilities: dict
    client_info: ClientInfo

    def to_json_dict(self) -> dict:
        values = {
            "protocolVersion": self.protocol_version,
            "capabilities": self.capabilities,
            "clientInfo": None if self.client_info is None else self.client_info.to_json_dict(),
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> InitializeParams:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to InitializeParams.")

        capabilities = _read(data, "capabilities")
        client_info = _read(data, "clientInfo")

        if capabilities is _MISSING or capabilities is None:
            capabilities = None
        elif not isinstance(capabilities, dict):
            raise ValueError("The JSON value could not be converted to JsonObject.")

        return cls(
            protocol_version=_as_string(_read(data, "protocolVersion")),
            capabilities=capabilities,
            client_info=(
                None if client_info is _MISSING or client_info is None
                else ClientInfo.from_json_dict(client_info)))


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
