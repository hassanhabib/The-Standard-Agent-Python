# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from http import HTTPStatus

from restfulsense import HttpRequestException
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference


class ScriptedGeneratorBroker(GeneratorBroker):
    """The scripted Brain: its replies in order, repeating the last once they run out.

    It never opts in to the request (honors_request stays False), so it ignores the resolved
    inference it is handed, which is how graceful degradation is certified against the
    interface's real default rather than a simulation of it.
    """

    def __init__(self, replies: Sequence[str], transient_failures: int = 0) -> None:
        self._replies = replies
        self._index = 0
        self._remaining_transient_failures = transient_failures

    async def generate(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> str:
        # A scripted transient failure, raised as the category the framework localizes a
        # dependency failure into, so retry is certified on the classification it actually
        # uses, not on a message it happens to match (SPEC.md 4.10).
        if self._remaining_transient_failures > 0:
            self._remaining_transient_failures -= 1

            raise HttpRequestException(
                "scripted transient failure",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE)

        return self._next_reply()

    async def generate_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> AsyncIterator[str]:
        yield self._next_reply()

    def _next_reply(self) -> str:
        reply = self._replies[min(self._index, len(self._replies) - 1)]
        self._index += 1

        return reply
