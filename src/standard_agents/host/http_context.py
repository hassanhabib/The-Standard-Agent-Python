# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field

from standard_agents.host.security.claims import ClaimsPrincipal


@dataclass(frozen=True)
class HttpContext:
    """What the host knows about the request being served that code below it may ask about."""

    user: ClaimsPrincipal = field(default_factory=ClaimsPrincipal)


class HttpContextAccessor:
    """The request being served, wherever the code that asks runs.

    The server sets the context for the task that serves a request, so an agent's principal
    callable, called deep inside a run, reads the request that started the run and never
    another's. Each accessor holds its own context variable: a host and the resolver it hands
    the agent share one accessor, and two hosts in one process never see each other's requests.
    None outside a request, as when the agent runs from a background job.
    """

    def __init__(self) -> None:
        self._current: ContextVar[HttpContext | None] = ContextVar("http_context", default=None)

    @property
    def http_context(self) -> HttpContext | None:
        return self._current.get()

    @http_context.setter
    def http_context(self, http_context: HttpContext | None) -> None:
        self._current.set(http_context)
