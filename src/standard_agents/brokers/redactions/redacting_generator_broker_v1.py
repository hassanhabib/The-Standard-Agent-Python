# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
from typing import Mapping, MutableMapping, Sequence

from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.brokers.redactions.redaction_broker import RedactionBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ModelToolCall,
    ToolDefinition)


class RedactingGeneratorBrokerV1(GeneratorBrokerV1):
    """The same guarantee on the native path.

    4.6 says every model call, and a second contract is still a model call: the tool-call
    arguments coming back are rehydrated too, because a value the model echoed into an argument
    is a value that reaches a tool. And the whole message goes out redacted, not only its prose:
    a replayed tool call carries arguments that were rehydrated for the tool on an earlier turn,
    so they are tokenized again like the text around them. The 2026-09-04 principal review
    (F-02) found them going out in the clear.
    """

    def __init__(
            self,
            generator_broker: GeneratorBrokerV1,
            redaction_broker: RedactionBroker) -> None:

        self._generator_broker = generator_broker
        self._redaction_broker = redaction_broker

    @property
    def honors_request(self) -> bool:
        """The wrapped broker's flag, passed through explicitly.

        Never the interface's default: a decorator that leaned on the default member would
        degrade HERE and silently drop the resolved options before the wire.
        """
        return self._generator_broker.honors_request

    async def generate(
            self,
            messages: Sequence[ConversationMessage],
            tools: Sequence[ToolDefinition],
            *,
            inference: ResolvedInference | None = None) -> GenerationResult:

        vault: dict[str, str] = {}

        redacted_messages = tuple(self._redact_message(message, vault) for message in messages)

        result = await self._generator_broker.generate(
            redacted_messages,
            tools,
            inference=inference)

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
