# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference


class GeneratorBroker(ABC):
    """The brain: a system prompt and a user prompt in, the model's text out.

    ``inference`` carries the run's resolved inference options, precedence already applied at
    the boundary, so a broker writes what it is given and decides nothing. A broker that has not
    opted in (``honors_request`` is False) ignores it and the answer is still held to shape,
    because the Contract guardian validates and revises regardless
    (docs/per-request-inference.md 5). Provider packages keep working and opt in on their own
    schedule.
    """

    @abstractmethod
    async def generate(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> str:
        ...

    @abstractmethod
    def generate_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> AsyncIterator[str]:
        """The streamed twin, carrying the same options.

        A control a caller can step around by changing method is not a control (SPEC.md 7.6).
        """

    @property
    def honors_request(self) -> bool:
        """True when this broker puts resolved inference options on the wire.

        Constrained decoding is an optimization over a guarantee the architecture already
        provides; this flag exists so the trace can say which one happened.
        """
        return False
