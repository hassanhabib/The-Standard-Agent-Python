# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import AsyncIterator, Mapping

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.redactions.redaction_broker import RedactionBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference


class RedactingGeneratorBroker(GeneratorBroker):
    """Redaction at the wire, by decoration (SPEC.md 4.6).

    It used to live inside BrainService, GateService and JudgeService: three foundations each
    holding a second broker, and an invariant that read "every model call is redacted" but was
    really "three services each remembered to". Wrapping the generator instead makes it true by
    construction: the service above holds one broker and does not know redaction exists, and a
    fourth model call added tomorrow cannot forget.
    """

    def __init__(
            self,
            generator_broker: GeneratorBroker,
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
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> str:
        """Redact both prompts, generate, and rehydrate the reply.

        The vault is per call. Two prompts share it, so the same value redacts to the same
        token in both and the model can still tell they refer to one thing. The inference
        options travel unredacted: they are knobs and schemas the host or caller wrote, not
        conversation carrying PII, and a redacted schema would constrain the model to shapes
        nobody asked for.
        """
        vault: dict[str, str] = {}

        reply = await self._generator_broker.generate(
            self._redaction_broker.redact(system_prompt, vault),
            self._redaction_broker.redact(user_prompt, vault),
            inference=inference)

        return self._redaction_broker.rehydrate(reply, vault)

    async def generate_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> AsyncIterator[str]:

        vault: dict[str, str] = {}

        redacted_system_prompt = self._redaction_broker.redact(system_prompt, vault)
        redacted_user_prompt = self._redaction_broker.redact(user_prompt, vault)

        tokens = self._generator_broker.generate_stream(
            redacted_system_prompt,
            redacted_user_prompt,
            inference=inference)

        # The text held back until a placeholder split across tokens can be restored.
        pending: list[str] = []

        async for token in tokens:
            if not vault:
                yield token

                continue

            pending.append(token)
            ready = self._drain_ready(pending, vault)

            if ready:
                yield ready

        if vault and "".join(pending):
            yield self._redaction_broker.rehydrate("".join(pending), vault)

    def _drain_ready(self, pending: list[str], vault: Mapping[str, str]) -> str:
        """Rehydrate the pending text and return what is safe to hand on.

        Streaming makes rehydration a boundary problem: a placeholder can arrive split across
        two tokens, so anything from the last unmatched "{{" onward is held back until more text
        arrives. Without it a token boundary mid-placeholder leaks "{{EMAIL_" to the caller and
        never restores the value.

        This buffering belongs to redaction, which is why it moved here with it. A service that
        knew nothing about redaction had no business owning it.
        """
        buffer = self._redaction_broker.rehydrate("".join(pending), vault)

        hold = buffer.rfind("{")

        while hold > 0 and buffer[hold - 1] == "{":
            hold -= 1

        ready = buffer[:hold] if hold >= 0 else buffer
        keep = buffer[hold:] if hold >= 0 else ""

        pending.clear()
        pending.append(keep)

        return ready
