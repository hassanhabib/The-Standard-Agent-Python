# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence
from http import HTTPStatus

from restfulsense import HttpRequestException
from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ModelToolCall,
    ToolDefinition)

from conformance.models.native_reply import NativeReply


class ScriptedNativeGeneratorBroker(GeneratorBrokerV1):
    """A scripted V1 model: each reply is either a tool call or an answer, taken in order.

    It records the conversation it was handed on every call, because that is what the
    round-trip vector actually asserts. A generator that only returned scripted replies could not
    tell a framework that hands back a tool message naming the call from one that narrates the
    result as prose, and the difference between those two is the whole point of native tool
    calling.
    """

    def __init__(self, replies: Sequence[NativeReply], transient_failures: int = 0) -> None:
        self._replies = replies
        self._index = 0
        self._remaining_transient_failures = transient_failures
        self._conversations: list[Sequence[ConversationMessage]] = []
        self.last_tools: Sequence[ToolDefinition] = ()

    @property
    def conversations(self) -> Sequence[Sequence[ConversationMessage]]:
        return self._conversations

    async def generate(
            self,
            messages: Sequence[ConversationMessage],
            tools: Sequence[ToolDefinition],
            *,
            inference: ResolvedInference | None = None) -> GenerationResult:
        self._conversations.append(messages)
        self.last_tools = tools

        # The same scripted transient failure the text-protocol Brain raises, so degradation is
        # certified on the native seam against the category the framework actually localizes
        # (SPEC.md 4.10): a control that holds on one protocol only is not a control.
        if self._remaining_transient_failures > 0:
            self._remaining_transient_failures -= 1

            raise HttpRequestException(
                "scripted transient failure",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE)

        if self._index < len(self._replies):
            reply = self._replies[self._index]
            self._index += 1
        else:
            reply = NativeReply(content="done")

        return GenerationResult(
            content=reply.content or "",
            narration=reply.narration or "",
            tool_calls=tuple(
                ModelToolCall(call.id, call.name, call.arguments_json)
                for call in reply.tool_calls or ()),
            prompt_tokens=reply.prompt_tokens,
            completion_tokens=reply.completion_tokens)
