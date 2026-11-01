# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class NativeToolCall:
    id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class NativeReply:
    """One scripted V1 reply, as a vector writes it: a tool call, an answer, or both."""

    REJECTS_UNKNOWN_PROPERTIES: ClassVar[bool] = True

    content: str | None = None
    tool_calls: list[NativeToolCall] | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    narration: str | None = None
