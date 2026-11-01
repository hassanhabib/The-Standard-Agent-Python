# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# The V1 generator contract's shape: a conversation of typed messages, and tools declared as
# data rather than described in prose.
#
# V0 sends one system prompt and one user prompt, and reads the model's choice out of the first
# line of its text (ACTION: / TOOL: / FINAL:). That works everywhere, which is why it stays the
# Core contract, but it forfeits what hosted models are actually trained on, cannot express
# parallel calls, and has no way to tie a result back to the call that asked for it. V1 exists
# for the providers that do better; V0 keeps working untouched, and the five provider packages
# compile against it until they choose to move.
class MessageRole(Enum):
    SYSTEM = 0
    USER = 1
    ASSISTANT = 2

    # A tool's result, tied to the call that asked for it by tool_call_id.
    TOOL = 3


# One call the model asked for. The id is what makes a result attributable to a request, which
# is the thing the text protocol cannot express.
@dataclass(frozen=True)
class ModelToolCall:
    id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class ConversationMessage:
    role: MessageRole = MessageRole.SYSTEM
    content: str = ""

    # Calls the assistant asked for, when it asked for any.
    tool_calls: tuple[ModelToolCall, ...] = ()

    # Which call this message answers: set on a MessageRole.TOOL message.
    tool_call_id: str = ""


# A tool offered to the model, as data rather than as a sentence in a prompt.
@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters_json: str


# What a V1 generation produced: text, tool calls, or both, and what it cost, when the
# provider says (SPEC.md 3.4).
@dataclass(frozen=True)
class GenerationResult:
    content: str = ""
    tool_calls: tuple[ModelToolCall, ...] = ()

    # User-voiced progress prose the model offered alongside its choice ("Let me check the
    # web..."). Optional: a provider that reports none leaves the default, and the text
    # protocol's SAY: line is this field's V0 twin.
    narration: str = ""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0
