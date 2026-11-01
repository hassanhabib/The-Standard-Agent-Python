# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import AsyncIterator, Mapping

from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.brokers.redactions.iredaction_broker import IRedactionBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference


# Redaction at the wire, by decoration (SPEC.md 4.6).
#
# It used to live inside BrainService, GateService and JudgeService: three foundations each
# holding a second broker, and an invariant that read "every model call is redacted" but was
# really "three services each remembered to". Wrapping the generator instead makes it true by
# construction: the service above holds one broker and does not know redaction exists, and a
# fourth model call added tomorrow cannot forget.
class RedactingGeneratorBroker(IGeneratorBroker):
    def __init__(
        self,
        generator_broker: IGeneratorBroker,
        redaction_broker: IRedactionBroker) -> None:

        self._generator_broker = generator_broker
        self._redaction_broker = redaction_broker

    # Explicit pass-throughs, never the interface's defaults: a decorator that leaned on the
    # default member would degrade HERE and silently drop the resolved options before the wire.
    @property
    def honors_request(self) -> bool:
        return self._generator_broker.honors_request

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        # The vault is per call. Two prompts share it, so the same value redacts to the same
        # token in both and the model can still tell they refer to one thing.
        vault: dict[str, str] = {}

        reply = await self._generator_broker.generate(
            self._redaction_broker.redact(system_prompt, vault),
            self._redaction_broker.redact(user_prompt, vault))

        return self._redaction_broker.rehydrate(reply, vault)

    # The inference options travel unredacted: they are knobs and schemas the host or caller
    # wrote, not conversation carrying PII, and a redacted schema would constrain the model to
    # shapes nobody asked for.
    async def generate_with_inference(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference) -> str:

        vault: dict[str, str] = {}

        reply = await self._generator_broker.generate_with_inference(
            self._redaction_broker.redact(system_prompt, vault),
            self._redaction_broker.redact(user_prompt, vault),
            inference)

        return self._redaction_broker.rehydrate(reply, vault)

    def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        return self._generate_stream(system_prompt, user_prompt, inference=None)

    def generate_stream_with_inference(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference) -> AsyncIterator[str]:

        return self._generate_stream(system_prompt, user_prompt, inference)

    async def _generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference | None) -> AsyncIterator[str]:

        vault: dict[str, str] = {}

        redacted_system_prompt = self._redaction_broker.redact(system_prompt, vault)
        redacted_user_prompt = self._redaction_broker.redact(user_prompt, vault)

        tokens = (
            self._generator_broker.generate_stream(
                redacted_system_prompt, redacted_user_prompt)
            if inference is None
            else self._generator_broker.generate_stream_with_inference(
                redacted_system_prompt, redacted_user_prompt, inference))

        # The pending text, as the StringBuilder the C# appends to.
        pending: list[str] = []

        async for token in tokens:
            if len(vault) == 0:
                yield token

                continue

            pending.append(token)
            ready = self._drain_ready(pending, vault)

            if len(ready) > 0:
                yield ready

        if len(vault) > 0 and len("".join(pending)) > 0:
            yield self._redaction_broker.rehydrate("".join(pending), vault)

    # Streaming makes rehydration a boundary problem: a placeholder can arrive split across two
    # tokens, so anything from the last unmatched "{{" onward is held back until more text
    # arrives. Without it a token boundary mid-placeholder leaks "{{EMAIL_" to the caller and
    # never restores the value.
    #
    # This buffering belongs to redaction, which is why it moved here with it. A service that
    # knew nothing about redaction had no business owning it.
    def _drain_ready(self, pending: list[str], vault: Mapping[str, str]) -> str:
        buffer = self._redaction_broker.rehydrate("".join(pending), vault)

        hold = buffer.rfind("{")

        while hold > 0 and buffer[hold - 1] == "{":
            hold -= 1

        ready = buffer[:hold] if hold >= 0 else buffer
        keep = buffer[hold:] if hold >= 0 else ""

        pending.clear()
        pending.append(keep)

        return ready
