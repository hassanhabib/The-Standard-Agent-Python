# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
from typing import Mapping, MutableMapping, Sequence

from standard_agents.brokers.generators.igenerator_broker_v1 import IGeneratorBrokerV1
from standard_agents.brokers.redactions.iredaction_broker import IRedactionBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ModelToolCall,
    ToolDefinition)


# The same guarantee on the native path. 4.6 says every model call, and a second contract is
# still a model call: the tool-call arguments coming back are rehydrated too, because a value
# the model echoed into an argument is a value that reaches a tool. And the whole message goes
# out redacted, not only its prose: a replayed tool call carries arguments that were rehydrated
# for the tool on an earlier turn, so they are tokenized again like the text around them. The
# 2026-09-04 principal review (F-02) found them going out in the clear.
class RedactingGeneratorBrokerV1(IGeneratorBrokerV1):
    def __init__(
        self,
        generator_broker: IGeneratorBrokerV1,
        redaction_broker: IRedactionBroker) -> None:

        self._generator_broker = generator_broker
        self._redaction_broker = redaction_broker

    # Explicit pass-throughs, never the interface's defaults: a decorator that leaned on the
    # default member would degrade HERE and silently drop the resolved options before the wire.
    @property
    def honors_request(self) -> bool:
        return self._generator_broker.honors_request

    async def generate(
        self,
        messages: Sequence[ConversationMessage],
        tools: Sequence[ToolDefinition]) -> GenerationResult:

        return await self._generate(messages, tools, inference=None)

    async def generate_with_inference(
        self,
        messages: Sequence[ConversationMessage],
        tools: Sequence[ToolDefinition],
        inference: ResolvedInference) -> GenerationResult:

        return await self._generate(messages, tools, inference)

    async def _generate(
        self,
        messages: Sequence[ConversationMessage],
        tools: Sequence[ToolDefinition],
        inference: ResolvedInference | None) -> GenerationResult:

        vault: dict[str, str] = {}

        redacted_messages = tuple(self._redact_message(message, vault) for message in messages)

        result = (
            await self._generator_broker.generate(redacted_messages, tools)
            if inference is None
            else await self._generator_broker.generate_with_inference(
                redacted_messages, tools, inference))

        return self._rehydrate_result(result, vault)

    def _redact_message(
        self,
        message: ConversationMessage,
        vault: MutableMapping[str, str]) -> ConversationMessage:

        return dataclasses.replace(
            message,
            content=self._redaction_broker.redact(message.content, vault),
            tool_calls=tuple(
                self._redact_tool_call(tool_call, vault) for tool_call in message.tool_calls))

    def _redact_tool_call(
        self,
        tool_call: ModelToolCall,
        vault: MutableMapping[str, str]) -> ModelToolCall:

        return dataclasses.replace(
            tool_call,
            arguments_json=self._redaction_broker.redact(tool_call.arguments_json, vault))

    def _rehydrate_result(
        self,
        result: GenerationResult,
        vault: Mapping[str, str]) -> GenerationResult:

        return dataclasses.replace(
            result,
            content=self._redaction_broker.rehydrate(result.content, vault),
            tool_calls=tuple(
                self._rehydrate_tool_call(tool_call, vault) for tool_call in result.tool_calls))

    def _rehydrate_tool_call(
        self,
        tool_call: ModelToolCall,
        vault: Mapping[str, str]) -> ModelToolCall:

        return dataclasses.replace(
            tool_call,
            arguments_json=self._redaction_broker.rehydrate(tool_call.arguments_json, vault))
