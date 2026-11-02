# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from standard_agents.models.brokers.mcps.tool_call_content import ToolCallContent

_MISSING = object()


@dataclass(frozen=True)
class ToolCallResult:
    """What a tools/call returned: its content and any structured content.

    Wire names follow JsonNamingPolicy.CamelCase; reads are case-insensitive and null values are
    omitted on write (WhenWritingNull), as the HttpMcpBroker's serializer options leave them.
    """

    content: tuple[ToolCallContent, ...] | None

    # The parsed JSON it arrived as (a JsonElement?); None when absent or null.
    structured_content: Any | None

    def to_json_dict(self) -> dict:
        values = {
            "content": (
                None if self.content is None
                else [
                    None if item is None else item.to_json_dict()
                    for item in self.content]),
            "structuredContent": self.structured_content,
        }

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def from_json_dict(cls, data: dict) -> ToolCallResult:
        if not isinstance(data, dict):
            raise ValueError("The JSON value could not be converted to ToolCallResult.")

        content = _read_ignoring_case(data, "content")
        structured_content = _read_ignoring_case(data, "structuredContent")

        if content is _MISSING or content is None:
            parsed_content = None
        elif isinstance(content, list):
            parsed_content = tuple(
                None if item is None else ToolCallContent.from_json_dict(item)
                for item in content)
        else:
            raise ValueError(
                "The JSON value could not be converted to IReadOnlyList<ToolCallContent>.")

        return cls(
            content=parsed_content,
            structured_content=(
                None if structured_content is _MISSING else structured_content))


def _read_ignoring_case(data: dict, name: str) -> Any:
    """Read a property the way PropertyNameCaseInsensitive does.

    Every key that matches the name ignoring case is read, and the last one wins.
    """
    found = _MISSING

    for key, value in data.items():
        if key.lower() == name.lower():
            found = value

    return found
